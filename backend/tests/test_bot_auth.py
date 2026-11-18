from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_current_user
from app.models.models import Challenge, ChallengeDay, OneTimeCode, User
from app.routers import auth as auth_router
from app.routers import session as session_router
from app.schemas.auth import LoginRequest, SetPasswordRequest
from app.services.auth_service import (
    OtpRateLimitError,
    confirm_participation,
    create_otp_for_user,
    expire_and_promote_waitlist,
    generate_otp,
    register_telegram_user,
    verify_otp_for_user,
)
from conftest import run_coro


@pytest.fixture(autouse=True)
def _clear_login_attempts():
    yield


def _make_request(path: str):
    return SimpleNamespace(url=SimpleNamespace(path=path))


def test_generate_otp_format():
    for _ in range(50):
        code = generate_otp(10)
        assert len(code) == 10
        for ch in "0O1lI":
            assert ch not in code


def test_otp_single_use_and_expiry_and_rate_limit(db_session):
    async def _run():
        user = User(
            telegram_id=100001,
            phone="+998901112233",
            full_name="Test User",
            username="test_user",
            login="u100001",
            status="registered",
            must_change_password=True,
        )
        db_session.add(user)
        await db_session.commit()

        now = datetime.now(timezone.utc)

        # 1. Create OTP #1
        otp1 = await create_otp_for_user(db_session, user, now=now)
        await db_session.commit()

        # Plaintext is NOT stored in DB
        res = await db_session.execute(select(OneTimeCode).where(OneTimeCode.user_id == user.id))
        row = res.scalar_one()
        assert row.code_hash != otp1

        # 2. Create OTP #2 -> invalidates OTP #1
        otp2 = await create_otp_for_user(db_session, user, now=now + timedelta(minutes=1))
        await db_session.commit()
        assert not await verify_otp_for_user(db_session, user, otp1, now=now + timedelta(minutes=2))

        # 3. Expired OTP #2 fails
        assert not await verify_otp_for_user(
            db_session, user, otp2, now=now + timedelta(minutes=settings.OTP_TTL_MINUTES + 2)
        )

        # 4. Create OTP #3 (3rd in the hour) -> succeeds and works once
        otp3 = await create_otp_for_user(db_session, user, now=now + timedelta(minutes=3))
        await db_session.commit()
        assert await verify_otp_for_user(db_session, user, otp3, now=now + timedelta(minutes=4))
        await db_session.commit()
        assert not await verify_otp_for_user(db_session, user, otp3, now=now + timedelta(minutes=5))

        # 5. 4th OTP in same hour raises OtpRateLimitError
        with pytest.raises(OtpRateLimitError):
            await create_otp_for_user(db_session, user, now=now + timedelta(minutes=10))

    run_coro(_run())


def test_capacity_waitlist_and_promotion(db_session, monkeypatch):
    async def _run():
        monkeypatch.setattr(settings, "MAX_PARTICIPANTS", 2)
        now = datetime.now(timezone.utc)

        u1, otp1, pos1 = await register_telegram_user(
            db_session,
            telegram_id=2001,
            phone="+998901000001",
            full_name="User One",
            username="u1",
            self_level="beginner",
            age_group="student",
            region="Toshkent shahri",
            source="Telegram",
            interest="Web",
            consent_version=1,
            now=now,
        )
        u2, otp2, pos2 = await register_telegram_user(
            db_session,
            telegram_id=2002,
            phone="+998901000002",
            full_name="User Two",
            username="u2",
            self_level="basic",
            age_group="working",
            region="Samarqand",
            source="Instagram",
            interest="Data va AI",
            consent_version=1,
            now=now + timedelta(seconds=1),
        )
        u3, otp3, pos3 = await register_telegram_user(
            db_session,
            telegram_id=2003,
            phone="+998901000003",
            full_name="User Three",
            username="u3",
            self_level="intermediate",
            age_group="student",
            region="Buxoro",
            source="Do'stlar",
            interest="Telegram botlar",
            consent_version=1,
            now=now + timedelta(seconds=2),
        )
        await db_session.commit()

        assert u1.status == "registered" and otp1 is not None and pos1 is None
        assert u2.status == "registered" and otp2 is not None and pos2 is None
        assert u3.status == "waitlist" and otp3 is None and pos3 == 1

        # Confirm u1, leave u2 unconfirmed
        assert await confirm_participation(db_session, u1, now=now + timedelta(minutes=5))
        await db_session.commit()
        assert u1.status == "confirmed"

        # Expire initial unconfirmed (u2) and promote u3
        expired, promoted = await expire_and_promote_waitlist(
            db_session, expire_initial_registered=True, now=now + timedelta(days=1)
        )
        await db_session.commit()

        assert [u.id for u in expired] == [u2.id]
        assert len(promoted) == 1
        assert promoted[0][0].id == u3.id
        assert promoted[0][0].status == "registered"
        assert promoted[0][1] is not None

    run_coro(_run())


def test_auth_otp_login_must_change_password_and_confirmed_guard(db_session, monkeypatch):
    async def _run():
        monkeypatch.setattr(settings, "CHALLENGE_START_DATE", "2020-01-01")

        # 1. Legacy endpoints raise 410 Gone
        for fn in (
            auth_router.register_disabled,
            auth_router.forgot_password_disabled,
            auth_router.reset_password_disabled,
        ):
            with pytest.raises(HTTPException) as exc:
                await fn()
            assert exc.value.status_code == 410

        # 2. Register user via service -> gets OTP, status='registered'
        user, otp_plain, _ = await register_telegram_user(
            db_session,
            telegram_id=3001,
            phone="+998903334455",
            full_name="API Test User",
            username="apitester",
            self_level="beginner",
            age_group="student",
            region="Toshkent shahri",
            source="Telegram",
            interest="Web",
            consent_version=settings.RULES_VERSION,
        )
        challenge = Challenge(
            name="Test Challenge",
            total_days=1,
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            status="active",
            created_by=user.id,
        )
        db_session.add(challenge)
        await db_session.flush()
        day = ChallengeDay(challenge_id=challenge.id, day_number=1, title="Day 1", time_limit_secs=900)
        db_session.add(day)
        await db_session.commit()

        # 3. Login with login + OTP
        token_resp = await auth_router.login(LoginRequest(login=user.login, password=otp_plain), db=db_session)
        assert token_resp.must_change_password is True
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_resp.access_token)

        # 4. While must_change_password=True, /me and /set-password allowed, other paths -> 403
        me_user = await get_current_user(_make_request("/api/v1/auth/me"), creds, db_session)
        assert me_user.id == user.id

        with pytest.raises(HTTPException) as exc_403:
            await get_current_user(_make_request(f"/api/v1/challenges/{challenge.id}/my-progress"), creds, db_session)
        assert exc_403.value.status_code == 403

        # 5. Set new password -> must_change_password becomes False
        await auth_router.set_password(SetPasswordRequest(new_password="StrongPass123"), db_session, me_user)
        assert user.must_change_password is False

        # OTP cannot be reused; new password works
        with pytest.raises(HTTPException) as exc_reuse:
            await auth_router.login(LoginRequest(login=user.login, password=otp_plain), db=db_session)
        assert exc_reuse.value.status_code == 401

        ok_resp = await auth_router.login(LoginRequest(login=user.login, password="StrongPass123"), db=db_session)
        assert ok_resp.must_change_password is False

        # 6. User with status='registered' (not 'confirmed') cannot enter day
        with pytest.raises(HTTPException) as exc_status:
            await session_router.enter_day(str(day.id), db=db_session, current_user=user)
        assert exc_status.value.status_code == 403

    run_coro(_run())


def test_login_brute_force_lockout(db_session):
    async def _run():
        user = User(
            telegram_id=4001,
            phone="+998904445566",
            full_name="Lockout User",
            username="lockuser",
            login="u400001",
            status="confirmed",
            must_change_password=False,
        )
        db_session.add(user)
        await db_session.commit()

        for _ in range(5):
            with pytest.raises(HTTPException) as exc:
                await auth_router.login(LoginRequest(login="u400001", password="WrongPassword1"), db=db_session)
            assert exc.value.status_code == 401

        with pytest.raises(HTTPException) as exc_lock:
            await auth_router.login(LoginRequest(login="u400001", password="WrongPassword1"), db=db_session)
        assert exc_lock.value.status_code == 429

    run_coro(_run())
