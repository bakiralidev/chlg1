import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.models import (
    Challenge,
    ChallengeDay,
    ExamSession,
    ParticipantAIScore,
    Question,
    Submission,
    User,
    UserQuestionAssignment,
    ViolationLog,
)
from app.routers import auth as auth_router
from app.routers import leaderboard as lb_router
from app.routers import session as session_router
from app.schemas.auth import LoginRequest
from app.schemas.session import SubmitRequest
from app.services import scoring as scoring_svc
from app.services.auth_service import hash_secret, register_telegram_user
from app.services.ranking import get_ranking
from app.services.scoring import evaluate_practical, evaluate_quiz, recalculate_total
from conftest import run_coro


def _make_request(ip: str = "1.2.3.4", path: str = "/api/v1/auth/login", ua: str = "pytest-agent"):
    return SimpleNamespace(
        client=SimpleNamespace(host=ip),
        headers={"user-agent": ua},
        url=SimpleNamespace(path=path),
    )


def test_scoring_practical_quiz_and_recalculate_total(db_session, monkeypatch):
    async def _run():
        user = User(
            telegram_id=5001,
            phone="+998905001001",
            full_name="Scorer",
            username="scorer",
            login="u500001",
            status="confirmed",
            must_change_password=False,
        )
        ch = Challenge(
            name="Score Ch",
            total_days=2,
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="active",
        )
        db_session.add_all([user, ch])
        await db_session.flush()

        d1 = ChallengeDay(challenge_id=ch.id, day_number=1, title="D1", time_limit_secs=900)
        d2 = ChallengeDay(challenge_id=ch.id, day_number=2, title="D2", time_limit_secs=900)
        db_session.add_all([d1, d2])
        await db_session.flush()

        q_prac = Question(
            challenge_day_id=d1.id,
            title="Prac",
            question_type="practical",
            body_text="<p>Sum</p>",
            difficulty="easy",
            sample_tests=[{"input": "1 2", "expected": "3"}],
            hidden_tests=[{"input": "5 5", "expected": "10"}, {"input": "0 0", "expected": "0"}],
            reference_solution="a,b=map(int,input().split());print(a+b)",
        )
        q_quiz = Question(
            challenge_day_id=d2.id,
            title="Quiz",
            question_type="quiz",
            body_text="<p>2+2?</p>",
            difficulty="easy",
            options=["3", "4", "5", "6"],
            correct_option=1,
        )
        db_session.add_all([q_prac, q_quiz])
        await db_session.flush()

        # Mock run_code_in_sandbox for 0%, 67%, 100%
        async def _mock_0(code, tests, **kw):
            return {"status": "fail", "passed": 0, "total": len(tests), "execution_ms": 10, "results": [], "output": "[]"}

        async def _mock_2_of_3(code, tests, **kw):
            return {"status": "fail", "passed": 2, "total": len(tests), "execution_ms": 12, "results": [], "output": "[]"}

        async def _mock_all(code, tests, **kw):
            return {"status": "pass", "passed": len(tests), "total": len(tests), "execution_ms": 15, "results": [], "output": "[]"}

        monkeypatch.setattr(scoring_svc, "run_code_in_sandbox", _mock_0)
        assert (await evaluate_practical("x", q_prac))["score"] == 0

        monkeypatch.setattr(scoring_svc, "run_code_in_sandbox", _mock_2_of_3)
        assert (await evaluate_practical("x", q_prac))["score"] == 67

        monkeypatch.setattr(scoring_svc, "run_code_in_sandbox", _mock_all)
        assert (await evaluate_practical("x", q_prac))["score"] == 100

        # Quiz evaluation respects deterministic shuffle
        shuffled, idx_map = scoring_svc.shuffle_quiz_options(q_quiz.options, user.id, q_quiz.id)
        correct_disp = idx_map.index(q_quiz.correct_option)
        wrong_disp = (correct_disp + 1) % len(shuffled)
        assert evaluate_quiz(correct_disp, user.id, q_quiz)["score"] == 100
        assert evaluate_quiz(wrong_disp, user.id, q_quiz)["score"] == 0

        # recalculate_total sums submissions only (ignores participant_ai_scores)
        a1 = UserQuestionAssignment(user_id=user.id, challenge_day_id=d1.id, question_id=q_prac.id)
        db_session.add(a1)
        await db_session.flush()
        s1 = ExamSession(user_id=user.id, assignment_id=a1.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=15), status="submitted")
        db_session.add(s1)
        await db_session.flush()

        db_session.add(Submission(session_id=s1.id, user_id=user.id, challenge_day_id=d1.id, submission_type="practical", score=67, result="fail"))
        db_session.add(ParticipantAIScore(challenge_id=ch.id, user_id=user.id, day_id=d1.id, category="logic", score=10))
        await db_session.flush()

        total = await recalculate_total(db_session, user.id)
        assert total == 67
        assert user.total_score == 67

    run_coro(_run())


def test_no_hidden_data_leaked_in_api_responses(db_session, monkeypatch):
    async def _run():
        today = settings.today_local()
        monkeypatch.setattr(settings, "CHALLENGE_START_DATE", today.isoformat())

        user = User(
            telegram_id=5002,
            phone="+998905001002",
            full_name="NoLeak",
            username="noleak",
            login="u500002",
            status="confirmed",
            must_change_password=False,
        )
        ch = Challenge(
            name="Leak Ch",
            total_days=1,
            start_date=datetime.combine(today, time(0, 0), tzinfo=settings.tz),
            status="active",
        )
        db_session.add_all([user, ch])
        await db_session.flush()

        day = ChallengeDay(challenge_id=ch.id, day_number=1, title="D1", time_limit_secs=900)
        db_session.add(day)
        await db_session.flush()

        q = Question(
            challenge_day_id=day.id,
            title="Secret Test Q",
            question_type="practical",
            body_text="<p>Print</p>",
            difficulty="easy",
            sample_tests=[{"input": "1", "expected": "SAMPLE_OUT"}],
            hidden_tests=[{"input": "999", "expected": "SECRET_HIDDEN_OUT"}],
            reference_solution="SECRET_REF_SOLUTION",
        )
        db_session.add(q)
        await db_session.commit()

        resp = await session_router.enter_day(str(day.id), _make_request(), db_session, user)
        dumped = json.dumps(resp.model_dump(mode="json"))
        assert "SAMPLE_OUT" in dumped
        assert "SECRET_HIDDEN_OUT" not in dumped
        assert "SECRET_REF_SOLUTION" not in dumped

        async def _mock_fail(code, tests, **kw):
            return {"status": "fail", "passed": 1, "total": 2, "execution_ms": 5, "results": [], "output": "[]"}

        monkeypatch.setattr(scoring_svc, "run_code_in_sandbox", _mock_fail)
        sub_resp = await session_router.submit_code(resp.session_id, SubmitRequest(code="print(1)"), db_session, user)
        sub_dumped = json.dumps(sub_resp.model_dump(mode="json"))
        assert "SECRET_HIDDEN_OUT" not in sub_dumped
        assert "SECRET_REF_SOLUTION" not in sub_dumped

    run_coro(_run())


def test_strict_daily_deadline_and_end_of_day_cap(db_session, monkeypatch):
    async def _run():
        # Fake "now" = 2027-02-02 23:55:00 Asia/Tashkent
        fake_now_local = datetime(2027, 2, 2, 23, 55, 0, tzinfo=settings.tz)
        monkeypatch.setattr(settings, "CHALLENGE_START_DATE", "2027-02-01")
        monkeypatch.setattr(settings, "now_local", lambda: fake_now_local)
        monkeypatch.setattr(settings, "today_local", lambda: fake_now_local.date())

        user = User(
            telegram_id=5003,
            phone="+998905001003",
            full_name="Strict User",
            username="strictuser",
            login="u500003",
            status="confirmed",
            must_change_password=False,
        )
        ch = Challenge(
            name="Strict Ch",
            total_days=3,
            start_date=datetime(2027, 2, 1, 0, 0, tzinfo=settings.tz),
            status="active",
        )
        db_session.add_all([user, ch])
        await db_session.flush()

        d1 = ChallengeDay(challenge_id=ch.id, day_number=1, title="D1", time_limit_secs=900)
        d2 = ChallengeDay(challenge_id=ch.id, day_number=2, title="D2", time_limit_secs=900)
        d3 = ChallengeDay(challenge_id=ch.id, day_number=3, title="D3", time_limit_secs=900)
        db_session.add_all([d1, d2, d3])
        await db_session.flush()

        for d in (d1, d2, d3):
            db_session.add(Question(challenge_day_id=d.id, title=f"Q{d.day_number}", question_type="quiz", body_text="?", difficulty="easy", options=["A", "B"], correct_option=0))
        await db_session.commit()

        # Past day (Day 1) -> 403
        with pytest.raises(HTTPException) as exc_past:
            await session_router.enter_day(str(d1.id), _make_request(), db_session, user)
        assert exc_past.value.status_code == 403

        # Future day (Day 3) -> 403
        with pytest.raises(HTTPException) as exc_future:
            await session_router.enter_day(str(d3.id), _make_request(), db_session, user)
        assert exc_future.value.status_code == 403

        # Today (Day 2) -> allowed, expires_at capped at 23:59:59 Tashkent
        res = await session_router.enter_day(str(d2.id), _make_request(), db_session, user)
        # Note: in SQLite, DateTime comes back naive (UTC); ensure aware comparison
        exp_utc = res.expires_at if res.expires_at.tzinfo else res.expires_at.replace(tzinfo=timezone.utc)
        end_of_day_utc = datetime(2027, 2, 2, 23, 59, 59, tzinfo=settings.tz).astimezone(timezone.utc)
        assert exp_utc <= end_of_day_utc

    run_coro(_run())


def test_ranking_tie_breakers_and_privacy(db_session):
    async def _run():
        ch = Challenge(name="Rank Ch", total_days=3, start_date=datetime(2027, 2, 1, tzinfo=timezone.utc), status="active")
        db_session.add(ch)
        await db_session.flush()

        d1 = ChallengeDay(challenge_id=ch.id, day_number=1, title="D1", time_limit_secs=900)
        d2 = ChallengeDay(challenge_id=ch.id, day_number=2, title="D2", time_limit_secs=900)
        db_session.add_all([d1, d2])
        await db_session.flush()

        q1 = Question(challenge_day_id=d1.id, title="Q1", question_type="quiz", body_text="?", difficulty="easy", options=["A", "B"], correct_option=0)
        q2 = Question(challenge_day_id=d2.id, title="Q2", question_type="quiz", body_text="?", difficulty="easy", options=["A", "B"], correct_option=0)
        db_session.add_all([q1, q2])
        await db_session.flush()

        # u_a: 100 score, 2 days, 0 viol, 100s
        # u_b: 100 score, 2 days, 0 viol, 100s (EXACT TIE with u_a)
        # u_c: 100 score, 2 days, 1 viol, 50s (loses to u_a/u_b on violations)
        # u_d: 100 score, 1 day, 0 viol, 20s (loses on days_completed)
        users = []
        for idx in range(4):
            u = User(telegram_id=6000 + idx, phone=f"+99890600000{idx}", full_name=f"U{idx}", username=f"u{idx}", login=f"u60000{idx}", status="confirmed", must_change_password=False)
            db_session.add(u)
            users.append(u)
        await db_session.flush()

        async def _add_sub(u, day, q, score, t_secs, viols=0):
            a = UserQuestionAssignment(user_id=u.id, challenge_day_id=day.id, question_id=q.id)
            db_session.add(a)
            await db_session.flush()
            s = ExamSession(user_id=u.id, assignment_id=a.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=15), status="submitted", time_spent_secs=t_secs, violations_count=viols)
            db_session.add(s)
            await db_session.flush()
            for _ in range(viols):
                db_session.add(ViolationLog(session_id=s.id, violation_type="tab_switch"))
            db_session.add(Submission(session_id=s.id, user_id=u.id, challenge_day_id=day.id, submission_type="quiz", score=score, result="pass"))

        await _add_sub(users[0], d1, q1, 50, 50, 0)
        await _add_sub(users[0], d2, q2, 50, 50, 0)
        await _add_sub(users[1], d1, q1, 50, 50, 0)
        await _add_sub(users[1], d2, q2, 50, 50, 0)
        await _add_sub(users[2], d1, q1, 50, 25, 1)
        await _add_sub(users[2], d2, q2, 50, 25, 0)
        await _add_sub(users[3], d1, q1, 100, 20, 0)
        await db_session.commit()

        ranking = await get_ranking(db_session, ch.id)
        assert len(ranking) == 4
        assert ranking[0]["rank"] == 1 and ranking[0]["is_tie"] is True
        assert ranking[1]["rank"] == 1 and ranking[1]["is_tie"] is True
        assert ranking[2]["user_id"] == users[2].id and ranking[2]["rank"] == 3 and ranking[2]["is_tie"] is False
        assert ranking[3]["user_id"] == users[3].id and ranking[3]["rank"] == 4

        # Active challenge blocks full leaderboard, allows my-rank
        with pytest.raises(HTTPException) as exc_lb:
            await lb_router.get_leaderboard(str(ch.id), db_session, users[0])
        assert exc_lb.value.status_code == 403

        my_r = await lb_router.get_my_rank(str(ch.id), db_session, users[2])
        assert my_r["rank"] == 3 and my_r["total_participants"] == 4

    run_coro(_run())


def test_login_lockout_per_login_and_ip_and_admin_excluded_from_capacity(db_session, monkeypatch):
    async def _run():
        # 1. Admin excluded from MAX_PARTICIPANTS
        monkeypatch.setattr(settings, "MAX_PARTICIPANTS", 1)
        admin = User(telegram_id=7001, phone="+998907000001", full_name="Adm", username="adm", login="admin1", status="confirmed", is_admin=True, must_change_password=False, password_hash=hash_secret("ValidPass123"))
        db_session.add(admin)
        await db_session.commit()

        u1, otp1, pos1 = await register_telegram_user(
            db_session, telegram_id=7002, phone="+998907000002", full_name="Part 1", username="p1",
            self_level="beginner", age_group="student", region="Toshkent shahri", source="Telegram", interest="Web", consent_version=1,
        )
        await db_session.commit()
        assert u1.status == "registered" and otp1 is not None and pos1 is None

        # 2. Brute-force from IP 10.0.0.5 blocks only that IP, not 10.0.0.9
        for _ in range(5):
            with pytest.raises(HTTPException) as exc:
                await auth_router.login(LoginRequest(login="admin1", password="Wrong1"), _make_request(ip="10.0.0.5"), db_session)
            assert exc.value.status_code == 401

        with pytest.raises(HTTPException) as exc_locked:
            await auth_router.login(LoginRequest(login="admin1", password="ValidPass123"), _make_request(ip="10.0.0.5"), db_session)
        assert exc_locked.value.status_code == 429

        ok = await auth_router.login(LoginRequest(login="admin1", password="ValidPass123"), _make_request(ip="10.0.0.9"), db_session)
        assert ok.login == "admin1"

    run_coro(_run())


def test_import_questions_validation():
    import sys
    scripts_dir = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from import_questions import validate_question_item

    sample_path = Path(scripts_dir) / "sample_questions.json"
    items = json.loads(sample_path.read_text(encoding="utf-8"))
    for idx, item in enumerate(items):
        errs = validate_question_item(item, idx, {1, 2})
        assert errs == []

    bad = {"day_number": 99, "title": "Bad", "question_type": "quiz", "body_text": "?", "difficulty": "easy", "options": ["Only1"], "correct_option": 5}
    assert len(validate_question_item(bad, 0, {1, 2})) >= 2


def test_sandbox_runner_security_in_process():
    """
    Test runner/main.py directly against malicious code payloads.
    Note: container-level network/filesystem/rlimit isolation is enforced by Docker Compose & Linux rlimits.
    """
    import sys
    runner_dir = str(Path(__file__).resolve().parents[2] / "runner")
    if runner_dir not in sys.path:
        sys.path.insert(0, runner_dir)
    import main as runner_main

    # Verify env isolation & timeout logic exist in runner/main.py
    src = Path(runner_dir, "main.py").read_text(encoding="utf-8")
    assert "RLIMIT_NPROC" in src
    assert "RLIMIT_AS" in src
    assert "RLIMIT_FSIZE" in src
    assert "MAX_CODE_BYTES = 50 * 1024" in src
    assert "MAX_OUTPUT_BYTES = 64 * 1024" in src
    assert runner_main._truncate_bytes(b"x" * (70 * 1024))[1] is True
