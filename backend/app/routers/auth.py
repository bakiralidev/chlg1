from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ip_utils import get_client_ip
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.database import get_db
from app.models.models import LoginAttempt, LoginEvent, User
from app.schemas.auth import LoginRequest, SetPasswordRequest, TokenResponse
from app.services.auth_service import record_consent, verify_otp_for_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

_MAX_LOGIN_IP_ATTEMPTS = 5
_MAX_IP_TOTAL_ATTEMPTS = 30
_BLOCK_WINDOW = timedelta(minutes=10)


async def _check_login_rate_limit(db: AsyncSession, login_key: str, ip: str, now: datetime) -> None:
    cutoff = now - _BLOCK_WINDOW

    pair_res = await db.execute(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.login == login_key,
            LoginAttempt.ip == ip,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= cutoff,
        )
    )
    if int(pair_res.scalar() or 0) >= _MAX_LOGIN_IP_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Juda ko'p noto'g'ri urinish. 10 daqiqadan keyin urinib ko'ring.",
        )

    ip_res = await db.execute(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.ip == ip,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= cutoff,
        )
    )
    if int(ip_res.scalar() or 0) >= _MAX_IP_TOTAL_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ushbu IP manzildan juda ko'p noto'g'ri urinish. Keyinroq urinib ko'ring.",
        )


def _needs_consent(user: User) -> bool:
    if user.is_admin:
        return False
    return (user.consent_version or 0) < settings.RULES_VERSION


@router.post("/register", status_code=status.HTTP_410_GONE)
async def register_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Sayt orqali ro'yxatdan o'tish o'chirilgan. Telegram bot orqali ro'yxatdan o'ting.",
    )


@router.post("/forgot-password", status_code=status.HTTP_410_GONE)
async def forgot_password_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Email orqali parol tiklash o'chirilgan. Telegram botdan foydalaning.",
    )


@router.post("/reset-password", status_code=status.HTTP_410_GONE)
async def reset_password_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Email orqali parol tiklash o'chirilgan. Telegram botdan foydalaning.",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    login_value = data.login.strip()
    login_key = login_value.lower()
    client_ip = get_client_ip(request)
    user_agent = (request.headers.get("user-agent", "")[:500] if request else None)
    now = datetime.now(timezone.utc)

    await _check_login_rate_limit(db, login_key, client_ip, now)

    result = await db.execute(
        select(User).where(or_(User.login == login_value, User.email == login_value))
    )
    user = result.scalar_one_or_none()

    if not user:
        db.add(LoginAttempt(login=login_key, ip=client_ip, success=False, created_at=now))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkauntingiz bloklangan",
        )

    authenticated = False
    if user.password_hash and verify_password(data.password, user.password_hash):
        authenticated = True
    elif await verify_otp_for_user(db, user, data.password, now=now):
        authenticated = True

    if not authenticated:
        db.add(LoginAttempt(login=login_key, ip=client_ip, success=False, created_at=now))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    db.add(LoginAttempt(login=login_key, ip=client_ip, success=True, created_at=now))
    db.add(LoginEvent(user_id=user.id, ip=client_ip, user_agent=user_agent, created_at=now))
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        login=user.login,
        username=user.username,
        full_name=user.full_name,
        is_admin=bool(user.is_admin),
        status=user.status,
        must_change_password=bool(user.must_change_password),
        consent_version=user.consent_version,
        rules_version=settings.RULES_VERSION,
        needs_consent=_needs_consent(user),
    )


@router.post("/set-password")
async def set_password(
    data: SetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.password_hash = hash_password(data.new_password)
    current_user.must_change_password = False
    await db.commit()
    return {"message": "Yangi parol muvaffaqiyatli o'rnatildi", "must_change_password": False}


@router.post("/consent")
async def accept_consent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await record_consent(db, current_user, settings.RULES_VERSION)
    await db.commit()
    return {
        "ok": True,
        "consent_version": current_user.consent_version,
        "rules_version": settings.RULES_VERSION,
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "login": current_user.login,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "status": current_user.status,
        "must_change_password": bool(current_user.must_change_password),
        "consent_version": current_user.consent_version,
        "rules_version": settings.RULES_VERSION,
        "needs_consent": _needs_consent(current_user),
        "avatar_url": current_user.avatar_url,
        "level": current_user.level,
        "total_score": current_user.total_score,
        "is_admin": bool(current_user.is_admin),
    }
