import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import func, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import ConsentLog, OneTimeCode, User

# Ambiguous characters (0/O, 1/l/I) excluded
OTP_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Advisory lock key for participant capacity check
_CAPACITY_LOCK_ID = 84201937


class OtpRateLimitError(Exception):
    """Raised when user exceeds OTP_MAX_PER_HOUR."""


def hash_secret(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_secret(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def generate_otp(length: int = 10) -> str:
    return "".join(secrets.choice(OTP_ALPHABET) for _ in range(length))


async def generate_unique_login(db: AsyncSession, max_attempts: int = 20) -> str:
    for _ in range(max_attempts):
        candidate = f"u{secrets.randbelow(900000) + 100000}"
        res = await db.execute(select(User.id).where(User.login == candidate))
        if res.scalar_one_or_none() is None:
            return candidate
    # Fallback 8-char login if 6-digit space gets crowded
    for _ in range(max_attempts):
        candidate = f"u{secrets.randbelow(9000000) + 1000000}"
        res = await db.execute(select(User.id).where(User.login == candidate))
        if res.scalar_one_or_none() is None:
            return candidate
    raise RuntimeError("Unikal login yaratib bo'lmadi")


async def _acquire_capacity_lock(db: AsyncSession) -> None:
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        await db.execute(text(f"SELECT pg_advisory_xact_lock({_CAPACITY_LOCK_ID})"))


async def create_otp_for_user(
    db: AsyncSession,
    user: User,
    *,
    invalidate_permanent_password: bool = False,
    bypass_rate_limit: bool = False,
    now: Optional[datetime] = None,
) -> str:
    now = now or datetime.now(timezone.utc)

    if not bypass_rate_limit:
        one_hour_ago = now - timedelta(hours=1)
        count_res = await db.execute(
            select(func.count(OneTimeCode.id)).where(
                OneTimeCode.user_id == user.id,
                OneTimeCode.created_at >= one_hour_ago,
            )
        )
        recent_count = count_res.scalar() or 0
        if recent_count >= settings.OTP_MAX_PER_HOUR:
            raise OtpRateLimitError(
                f"Soatiga maksimal {settings.OTP_MAX_PER_HOUR} marta parol so'rash mumkin."
            )

    # Invalidate any previously unused OTPs
    await db.execute(
        update(OneTimeCode)
        .where(OneTimeCode.user_id == user.id, OneTimeCode.used_at.is_(None))
        .values(used_at=now)
    )

    if invalidate_permanent_password:
        user.password_hash = None
        user.must_change_password = True

    plain_otp = generate_otp(10)
    otp = OneTimeCode(
        user_id=user.id,
        code_hash=hash_secret(plain_otp),
        expires_at=now + timedelta(minutes=settings.OTP_TTL_MINUTES),
        created_at=now,
    )
    db.add(otp)
    await db.flush()
    return plain_otp


async def verify_otp_for_user(
    db: AsyncSession,
    user: User,
    plain_code: str,
    *,
    now: Optional[datetime] = None,
) -> bool:
    now = now or datetime.now(timezone.utc)
    res = await db.execute(
        select(OneTimeCode)
        .where(
            OneTimeCode.user_id == user.id,
            OneTimeCode.used_at.is_(None),
            OneTimeCode.expires_at > now,
        )
        .order_by(OneTimeCode.created_at.desc())
    )
    active_otps = res.scalars().all()
    for otp in active_otps:
        if verify_secret(plain_code, otp.code_hash):
            otp.used_at = now
            user.must_change_password = True
            await db.flush()
            return True
    return False


async def get_waitlist_position(db: AsyncSession, user: User) -> Optional[int]:
    if user.status != "waitlist" or user.waitlisted_at is None:
        return None
    res = await db.execute(
        select(func.count(User.id)).where(
            User.status == "waitlist",
            User.waitlisted_at <= user.waitlisted_at,
        )
    )
    return int(res.scalar() or 1)


async def register_telegram_user(
    db: AsyncSession,
    *,
    telegram_id: int,
    phone: str,
    full_name: str,
    username: Optional[str],
    self_level: str,
    age_group: str,
    region: str,
    source: str,
    interest: str,
    consent_version: int,
    consent_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> tuple[User, Optional[str], Optional[int]]:
    """
    Create a new user from Telegram registration inside the current transaction.
    Returns (user, plain_otp_or_none, waitlist_position_or_none).
    """
    now = now or datetime.now(timezone.utc)
    consent_at = consent_at or now

    await _acquire_capacity_lock(db)

    active_count_res = await db.execute(
        select(func.count(User.id)).where(User.status.in_(["registered", "confirmed"]))
    )
    active_count = int(active_count_res.scalar() or 0)

    login = await generate_unique_login(db)
    is_admin = telegram_id in settings.admin_telegram_id_set
    has_slot = active_count < settings.MAX_PARTICIPANTS

    user = User(
        telegram_id=telegram_id,
        phone=phone,
        full_name=full_name,
        username=(username or full_name)[:100],
        login=login,
        password_hash=None,
        must_change_password=True,
        status="registered" if has_slot else "waitlist",
        consent_version=consent_version,
        consent_at=consent_at,
        self_level=self_level,
        age_group=age_group,
        region=region,
        source=source,
        interest=interest,
        waitlisted_at=None if has_slot else now,
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()

    db.add(ConsentLog(user_id=user.id, rules_version=consent_version, agreed_at=consent_at))

    if has_slot:
        otp_plain = await create_otp_for_user(
            db, user, invalidate_permanent_password=False, bypass_rate_limit=True, now=now
        )
        return user, otp_plain, None

    position = await get_waitlist_position(db, user)
    return user, None, position


async def confirm_participation(
    db: AsyncSession,
    user: User,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """Confirm a registered user. Returns True if newly confirmed."""
    if user.status != "registered":
        return False
    now = now or datetime.now(timezone.utc)
    user.status = "confirmed"
    user.confirmed_at = now
    await db.flush()
    return True


async def expire_and_promote_waitlist(
    db: AsyncSession,
    *,
    expire_initial_registered: bool = False,
    now: Optional[datetime] = None,
) -> tuple[list[User], list[tuple[User, str]]]:
    """
    1) Expire unconfirmed 'registered' users:
       - If expire_initial_registered=True (after CONFIRM_WINDOW_END 23:59): expire all 'registered' with promoted_at IS NULL.
       - Always expire promoted 'registered' users whose promoted_at + 24h < now.
    2) Promote waitlist users (ordered by waitlisted_at ASC) into free slots up to MAX_PARTICIPANTS.
    Returns (expired_users, [(promoted_user, otp_plain), ...]).
    """
    now = now or datetime.now(timezone.utc)
    await _acquire_capacity_lock(db)

    expired_users: list[User] = []

    if expire_initial_registered:
        res_initial = await db.execute(
            select(User).where(User.status == "registered", User.promoted_at.is_(None))
        )
        for u in res_initial.scalars().all():
            u.status = "expired"
            expired_users.append(u)

    cutoff_24h = now - timedelta(hours=24)
    res_promoted = await db.execute(
        select(User).where(
            User.status == "registered",
            User.promoted_at.is_not(None),
            User.promoted_at < cutoff_24h,
        )
    )
    for u in res_promoted.scalars().all():
        u.status = "expired"
        expired_users.append(u)

    await db.flush()

    active_count_res = await db.execute(
        select(func.count(User.id)).where(User.status.in_(["registered", "confirmed"]))
    )
    active_count = int(active_count_res.scalar() or 0)
    free_slots = max(0, settings.MAX_PARTICIPANTS - active_count)

    promoted_list: list[tuple[User, str]] = []
    if free_slots > 0:
        waitlist_res = await db.execute(
            select(User)
            .where(User.status == "waitlist")
            .order_by(User.waitlisted_at.asc())
            .limit(free_slots)
        )
        for u in waitlist_res.scalars().all():
            u.status = "registered"
            u.promoted_at = now
            otp_plain = await create_otp_for_user(
                db, u, invalidate_permanent_password=True, bypass_rate_limit=True, now=now
            )
            promoted_list.append((u, otp_plain))

    await db.flush()
    return expired_users, promoted_list


async def record_consent(
    db: AsyncSession,
    user: User,
    rules_version: int,
    *,
    now: Optional[datetime] = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    user.consent_version = rules_version
    user.consent_at = now
    db.add(ConsentLog(user_id=user.id, rules_version=rules_version, agreed_at=now))
    await db.flush()
