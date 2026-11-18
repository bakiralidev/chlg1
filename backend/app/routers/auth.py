from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.database import get_db
from app.models.models import User
from app.schemas.auth import LoginRequest, SetPasswordRequest, TokenResponse
from app.services.auth_service import record_consent, verify_otp_for_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# In-memory login brute-force protection: {login_key: {"count": int, "blocked_until": datetime | None}}
_MAX_LOGIN_ATTEMPTS = 5
_BLOCK_DURATION = timedelta(minutes=10)
_login_attempts: dict[str, dict] = {}


def _check_login_rate_limit(login_key: str, now: datetime) -> None:
    entry = _login_attempts.get(login_key)
    if not entry:
        return
    blocked_until = entry.get("blocked_until")
    if blocked_until and blocked_until > now:
        remaining_mins = max(1, int((blocked_until - now).total_seconds() // 60) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Juda ko'p noto'g'ri urinish. {remaining_mins} daqiqadan keyin urinib ko'ring."
        )
    if blocked_until and blocked_until <= now:
        _login_attempts.pop(login_key, None)


def _record_failed_login(login_key: str, now: datetime) -> None:
    entry = _login_attempts.get(login_key, {"count": 0, "blocked_until": None})
    entry["count"] = entry.get("count", 0) + 1
    if entry["count"] >= _MAX_LOGIN_ATTEMPTS:
        entry["blocked_until"] = now + _BLOCK_DURATION
    _login_attempts[login_key] = entry


def _clear_failed_logins(login_key: str) -> None:
    _login_attempts.pop(login_key, None)


def _needs_consent(user: User) -> bool:
    if user.is_admin:
        return False
    return (user.consent_version or 0) < settings.RULES_VERSION


@router.post("/register", status_code=status.HTTP_410_GONE)
async def register_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Sayt orqali ro'yxatdan o'tish o'chirilgan. Telegram bot orqali ro'yxatdan o'ting."
    )


@router.post("/forgot-password", status_code=status.HTTP_410_GONE)
async def forgot_password_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Email orqali parol tiklash o'chirilgan. Telegram botdan foydalaning."
    )


@router.post("/reset-password", status_code=status.HTTP_410_GONE)
async def reset_password_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Email orqali parol tiklash o'chirilgan. Telegram botdan foydalaning."
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    login_value = data.login.strip()
    login_key = login_value.lower()
    now = datetime.now(timezone.utc)

    _check_login_rate_limit(login_key, now)

    result = await db.execute(
        select(User).where(or_(User.login == login_value, User.email == login_value))
    )
    user = result.scalar_one_or_none()

    if not user:
        _record_failed_login(login_key, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri"
        )

    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkauntingiz bloklangan"
        )

    authenticated = False
    if user.password_hash and verify_password(data.password, user.password_hash):
        authenticated = True
    elif await verify_otp_for_user(db, user, data.password, now=now):
        authenticated = True
        await db.commit()
        await db.refresh(user)

    if not authenticated:
        _record_failed_login(login_key, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri"
        )

    _clear_failed_logins(login_key)
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
