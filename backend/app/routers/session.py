import random
import uuid
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ip_utils import get_client_ip
from app.core.rate_limit import enforce_run_rate_limit
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.models import (
    Challenge,
    ChallengeDay,
    ExamSession,
    Question,
    Submission,
    User,
    UserQuestionAssignment,
    ViolationLog,
)
from app.schemas.session import (
    AutosaveRequest,
    ChallengeProgressResponse,
    EnterDayResponse,
    MyDayStatus,
    RunCodeRequest,
    RunCodeResponse,
    SubmitRequest,
    SubmitResponse,
    TypingStartRequest,
    ViolationRequest,
    ViolationResponse,
)
from app.services.ranking import get_user_rank
from app.services.sandbox_service import RunnerUnavailableError, execute_python_code
from app.services.scoring import (
    evaluate_practical,
    evaluate_quiz,
    get_question_tests,
    recalculate_total,
    shuffle_quiz_options,
)

router = APIRouter(prefix="/api/v1", tags=["Session"])


def _local_date(dt: datetime):
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(settings.tz).date()


def _end_of_today_utc() -> datetime:
    today_local = settings.today_local()
    end_local = datetime.combine(today_local, time(23, 59, 59), tzinfo=settings.tz)
    return end_local.astimezone(timezone.utc)


def _safe_question_payload(question: Question, user_id) -> dict:
    """Return only participant-safe question fields (never hidden tests, correct_option, or reference_solution)."""
    samples, _ = get_question_tests(question)
    safe_samples = [
        {"input": tc.get("input", ""), "expected": tc.get("expected", "")}
        for tc in samples
    ] if samples else None

    shuffled_options = None
    if question.question_type == "quiz" and question.options:
        shuffled_options, _ = shuffle_quiz_options(list(question.options), user_id, question.id)

    return {
        "sample_tests": safe_samples,
        "options": shuffled_options,
    }


@router.get("/challenges")
async def list_active_challenges(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Challenge).where(Challenge.status == "active").order_by(Challenge.start_date)
    )
    challenges = result.scalars().all()
    now = settings.now_local()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "total_days": c.total_days,
            "start_date": c.start_date,
            "end_date": c.start_date + timedelta(days=c.total_days),
            "prize_info": c.prize_info,
            "is_started": (
                c.start_date.astimezone(settings.tz)
                if c.start_date.tzinfo
                else c.start_date.replace(tzinfo=settings.tz)
            ) <= now,
        }
        for c in challenges
    ]


@router.get("/challenges/{challenge_id}/my-progress", response_model=ChallengeProgressResponse)
async def my_progress(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ch = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = ch.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    days_result = await db.execute(
        select(ChallengeDay)
        .where(ChallengeDay.challenge_id == challenge_id)
        .order_by(ChallengeDay.day_number)
    )
    days = days_result.scalars().all()

    today = settings.today_local()
    day_statuses = []
    total_my_score = 0

    for day in days:
        day_date = _local_date(challenge.start_date) + timedelta(days=day.day_number - 1)
        opens_on = day_date.isoformat()
        is_today = day_date == today
        is_locked = day_date > today

        sub_q = await db.execute(
            select(Submission)
            .join(ExamSession, Submission.session_id == ExamSession.id)
            .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
            .where(
                UserQuestionAssignment.user_id == current_user.id,
                UserQuestionAssignment.challenge_day_id == day.id,
            )
            .order_by(Submission.submitted_at.desc())
        )
        submission = sub_q.scalar_one_or_none()

        sess_q = await db.execute(
            select(ExamSession)
            .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
            .where(
                UserQuestionAssignment.user_id == current_user.id,
                UserQuestionAssignment.challenge_day_id == day.id,
            )
        )
        session = sess_q.scalar_one_or_none()

        is_completed = submission is not None
        is_disqualified = session is not None and session.status == "disqualified"
        is_expired = day_date < today and not is_completed and not is_disqualified

        score = submission.score if submission else None
        if score:
            total_my_score += score

        day_statuses.append(
            MyDayStatus(
                day_id=str(day.id),
                day_number=day.day_number,
                title=day.title,
                time_limit_secs=day.time_limit_secs,
                is_today=is_today,
                is_locked=is_locked,
                is_expired=is_expired,
                is_completed=is_completed,
                is_disqualified=is_disqualified,
                score=score,
                opens_on=opens_on,
            )
        )

    rank_info = await get_user_rank(db, challenge.id, current_user.id)

    return ChallengeProgressResponse(
        challenge_id=str(challenge.id),
        challenge_name=challenge.name,
        total_days=challenge.total_days,
        days=day_statuses,
        my_total_score=total_my_score,
        my_rank=rank_info["rank"] if rank_info else None,
        total_participants=rank_info["total_participants"] if rank_info else None,
    )


@router.post("/days/{day_id}/enter", response_model=EnterDayResponse)
async def enter_day(
    day_id: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    day = None
    try:
        uuid_obj = uuid.UUID(day_id)
        day_result = await db.execute(select(ChallengeDay).where(ChallengeDay.id == uuid_obj))
        day = day_result.scalar_one_or_none()
    except (ValueError, TypeError):
        pass

    if not day:
        raise HTTPException(status_code=404, detail="Kun topilmadi")

    ch_result = await db.execute(select(Challenge).where(Challenge.id == day.challenge_id))
    challenge = ch_result.scalar_one_or_none()
    if not challenge or challenge.status != "active":
        raise HTTPException(status_code=400, detail="Bu challenge hozir faol emas")

    if not current_user.is_admin and current_user.status != "confirmed":
        status_messages = {
            "registered": "Qatnashishni tasdiqlamadingiz. Telegram botda 'Tayyorman' tugmasini bosing.",
            "waitlist": "Siz kutish ro'yxatidasiz. Joy bo'shaganda Telegram bot orqali xabar beriladi.",
            "expired": "Tasdiqlash muddati tugagan. Challenge'ga kirish mumkin emas.",
            "disqualified": "Siz diskvalifikatsiya qilingansiz.",
            "banned": "Akkauntingiz bloklangan.",
        }
        raise HTTPException(
            status_code=403,
            detail=status_messages.get(current_user.status, "Challenge'ga kirishga ruxsat yo'q"),
        )

    now = settings.now_local().astimezone(timezone.utc)
    today = settings.today_local()
    if not current_user.is_admin and today < settings.challenge_start:
        raise HTTPException(
            status_code=403,
            detail=f"Challenge hali boshlanmagan. {settings.CHALLENGE_START_DATE} kuni boshlanadi",
        )

    day_date = _local_date(challenge.start_date) + timedelta(days=day.day_number - 1)
    if day_date > today:
        raise HTTPException(
            status_code=403,
            detail=f"Bu kun hali ochilmagan. {day_date.isoformat()} kuni (00:00 Toshkent) ochiladi",
        )
    if day_date < today:
        raise HTTPException(status_code=403, detail="Bu kunning muddati tugagan")

    assign_result = await db.execute(
        select(UserQuestionAssignment).where(
            UserQuestionAssignment.user_id == current_user.id,
            UserQuestionAssignment.challenge_day_id == day.id,
        )
    )
    assignment = assign_result.scalar_one_or_none()

    if not assignment:
        q_result = await db.execute(
            select(Question).where(Question.challenge_day_id == day.id)
        )
        questions = q_result.scalars().all()
        if not questions:
            raise HTTPException(status_code=404, detail="Bu kun uchun savol qo'shilmagan")

        counts_res = await db.execute(
            select(
                UserQuestionAssignment.question_id,
                func.count(UserQuestionAssignment.id),
            )
            .where(UserQuestionAssignment.challenge_day_id == day.id)
            .group_by(UserQuestionAssignment.question_id)
        )
        assigned_counts = dict(counts_res.all())
        min_count = min(assigned_counts.get(q.id, 0) for q in questions)
        least_assigned = [q for q in questions if assigned_counts.get(q.id, 0) == min_count]
        chosen = random.choice(least_assigned)
        assignment = UserQuestionAssignment(
            user_id=current_user.id,
            challenge_day_id=day.id,
            question_id=chosen.id,
        )
        db.add(assignment)
        await db.flush()

    q_res = await db.execute(select(Question).where(Question.id == assignment.question_id))
    question = q_res.scalar_one()
    safe_q = _safe_question_payload(question, current_user.id)

    sess_result = await db.execute(
        select(ExamSession).where(ExamSession.assignment_id == assignment.id)
    )
    session = sess_result.scalar_one_or_none()

    if session:
        if session.status in ("disqualified", "submitted", "auto_submitted", "expired") or session.expires_at < now:
            if session.status == "active" and session.expires_at < now:
                session.status = "expired"
                session.is_readonly = True
            sub_res = await db.execute(
                select(Submission)
                .where(Submission.session_id == session.id)
                .order_by(Submission.submitted_at.desc())
            )
            submission = sub_res.scalar_one_or_none()
            await db.commit()
            return EnterDayResponse(
                session_id=str(session.id),
                expires_at=session.expires_at,
                entered_at=session.entered_at,
                question_id=str(question.id),
                question_title=question.title,
                question_type=question.question_type,
                question_body=question.body_text,
                starter_code=question.starter_code or "",
                sample_tests=safe_q["sample_tests"],
                options=safe_q["options"],
                time_limit_secs=day.time_limit_secs,
                is_readonly=True,
                previous_code=session.final_code,
                previous_note=session.note_content,
                previous_score=submission.score if submission else 0,
                violations_count=session.violations_count,
                max_violations=challenge.max_violations,
            )
    else:
        # Cap expires_at at 23:59:59 Asia/Tashkent of today
        end_of_day_utc = _end_of_today_utc()
        expires_at = min(now + timedelta(seconds=day.time_limit_secs), end_of_day_utc)
        client_ip = get_client_ip(request)
        user_agent = (request.headers.get("user-agent", "")[:500] if request else None)
        session = ExamSession(
            user_id=current_user.id,
            assignment_id=assignment.id,
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(session)

    await db.commit()
    await db.refresh(session)

    return EnterDayResponse(
        session_id=str(session.id),
        expires_at=session.expires_at,
        entered_at=session.entered_at,
        question_id=str(question.id),
        question_title=question.title,
        question_type=question.question_type,
        question_body=question.body_text,
        starter_code=question.starter_code or "",
        sample_tests=safe_q["sample_tests"],
        options=safe_q["options"],
        time_limit_secs=day.time_limit_secs,
        is_readonly=False,
        previous_code=session.final_code,
        previous_note=session.note_content,
        violations_count=session.violations_count,
        max_violations=challenge.max_violations,
    )


@router.patch("/sessions/{session_id}/typing-start")
async def typing_start(
    session_id: str,
    data: TypingStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user.id, db)
    if session.typing_started_at is None:
        session.typing_started_at = data.timestamp
        await db.commit()
    return {"ok": True}


@router.patch("/sessions/{session_id}/autosave")
async def autosave(
    session_id: str,
    data: AutosaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user.id, db)
    if data.code is not None:
        session.final_code = data.code
    if data.note_content is not None:
        session.note_content = data.note_content
    await db.commit()
    return {"ok": True, "saved_at": datetime.now(timezone.utc)}


@router.post("/sessions/{session_id}/violation", response_model=ViolationResponse)
async def report_violation(
    session_id: str,
    data: ViolationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user.id, db)

    log = ViolationLog(session_id=session.id, violation_type=data.violation_type)
    db.add(log)
    session.violations_count += 1

    assign_res = await db.execute(
        select(UserQuestionAssignment).where(UserQuestionAssignment.id == session.assignment_id)
    )
    assignment = assign_res.scalar_one()
    day_res = await db.execute(select(ChallengeDay).where(ChallengeDay.id == assignment.challenge_day_id))
    day = day_res.scalar_one()
    ch_res = await db.execute(select(Challenge).where(Challenge.id == day.challenge_id))
    challenge = ch_res.scalar_one()

    is_disqualified = session.violations_count >= challenge.max_violations
    if is_disqualified:
        session.status = "disqualified"
        session.is_readonly = True
        session.submitted_at = datetime.now(timezone.utc)

    await db.commit()

    return ViolationResponse(
        violations_count=session.violations_count,
        max_allowed=challenge.max_violations,
        is_disqualified=is_disqualified,
        message=(
            "Diskvalifikatsiya qilindingiz! Bu kun uchun 0 ball olasiz."
            if is_disqualified
            else f"Ogohlantirish {session.violations_count}/{challenge.max_violations}"
        ),
    )


@router.post("/sessions/{session_id}/run", response_model=RunCodeResponse)
async def run_session_code(
    session_id: str,
    data: RunCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enforce_run_rate_limit(str(current_user.id))

    session = await _get_active_session(session_id, current_user.id, db)
    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Sessiya vaqti tugagan")

    try:
        exec_result = await execute_python_code(
            code=data.code,
            input_data=data.input_data or "",
            timeout_seconds=settings.RUNNER_TIMEOUT_SECS,
        )
    except RunnerUnavailableError as err:
        raise HTTPException(status_code=503, detail=str(err))

    return RunCodeResponse(
        stdout=exec_result["stdout"],
        stderr=exec_result["stderr"],
        exit_code=exec_result["exit_code"],
        execution_ms=exec_result["execution_ms"],
        timed_out=exec_result.get("timed_out", False),
        truncated=exec_result.get("truncated", False),
    )


@router.post("/sessions/{session_id}/submit", response_model=SubmitResponse)
async def submit_code(
    session_id: str,
    data: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user.id, db)

    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now - timedelta(seconds=3):
        session.status = "expired"
        session.is_readonly = True
        await db.commit()
        raise HTTPException(status_code=400, detail="Vaqt tugagan. Yechim yuborilmadi.")

    assign_res = await db.execute(
        select(UserQuestionAssignment).where(UserQuestionAssignment.id == session.assignment_id)
    )
    assignment = assign_res.scalar_one()
    question_res = await db.execute(select(Question).where(Question.id == assignment.question_id))
    question = question_res.scalar_one()
    day_res = await db.execute(select(ChallengeDay).where(ChallengeDay.id == assignment.challenge_day_id))
    day = day_res.scalar_one()

    time_spent = None
    if session.typing_started_at:
        delta = now - session.typing_started_at
        time_spent = max(0, int(delta.total_seconds()))
    elif session.entered_at:
        entered = session.entered_at
        if entered.tzinfo is None:
            entered = entered.replace(tzinfo=timezone.utc)
        time_spent = max(0, int((now - entered).total_seconds()))

    passed_tests = None
    total_tests = None
    execution_ms = None
    docker_output = None
    original_selected = None

    if question.question_type == "practical":
        eval_res = await evaluate_practical(data.code or "", question)
        score = eval_res["score"]
        result_status = eval_res["result"]
        passed_tests = eval_res["passed"]
        total_tests = eval_res["total"]
        execution_ms = eval_res["execution_ms"]
        docker_output = eval_res["output"]
        msg = f"Yechim baholandi: {passed_tests}/{total_tests} test o'tdi ({score}/100 ball)."
    elif question.question_type == "quiz":
        eval_res = evaluate_quiz(data.selected_option, current_user.id, question)
        score = eval_res["score"]
        result_status = eval_res["result"]
        original_selected = eval_res["original_selected"]
        msg = "Javobingiz qabul qilindi!"
    else:
        score = 0
        result_status = "manual_review"
        msg = "Yechimingiz qabul qilindi. Admin tekshiruvidan keyin ball qo'yiladi."

    file_content = _build_submission_file(
        question=question,
        day=day,
        user=current_user,
        session=session,
        code=data.code,
        note_content=data.note_content,
        submitted_at=now,
        time_spent=time_spent,
    )

    submission = Submission(
        session_id=session.id,
        user_id=current_user.id,
        challenge_day_id=day.id,
        submission_type=question.question_type,
        code=data.code,
        note_content=data.note_content,
        selected_option=original_selected,
        file_content=file_content,
        result=result_status,
        score=score,
        execution_ms=execution_ms,
        docker_output=docker_output,
    )
    db.add(submission)

    session.status = "submitted"
    session.submitted_at = now
    session.final_code = data.code
    session.note_content = data.note_content
    session.time_spent_secs = time_spent
    session.is_readonly = True

    await db.flush()
    await recalculate_total(db, current_user.id)
    await db.commit()

    return SubmitResponse(
        result=result_status,
        score=score,
        execution_ms=execution_ms,
        passed_tests=passed_tests,
        total_tests=total_tests,
        message=msg,
    )


async def _get_active_session(session_id: str, user_id, db: AsyncSession) -> ExamSession:
    try:
        sess_uuid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Faol sessiya topilmadi")
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.id == sess_uuid,
            ExamSession.user_id == user_id,
            ExamSession.status == "active",
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Faol sessiya topilmadi")
    return session


def _build_submission_file(question, day, user, session, code, note_content, submitted_at, time_spent) -> str:
    lines = [
        "PYCHALLENGE SUBMISSION",
        "=" * 60,
        f"FOYDALANUVCHI: {user.username} ({user.login})",
        f"KUN: Day {day.day_number}  -  {day.title or ''}",
        f"SAVOL: {question.title}",
        f"SAVOL TURI: {question.question_type}",
        f"QIYINLIK: {question.difficulty}",
        "=" * 60,
        f"SESSIYAGA KIRISH: {session.entered_at}",
        f"YOZISHNI BOSHLASH: {session.typing_started_at or 'nomalum'}",
        f"YUBORISH VAQTI: {submitted_at}",
        f"SARFLANGAN VAQT: {time_spent or 'nomalum'} soniya",
        f"QOIDABUZARLIKLAR: {session.violations_count}",
        "=" * 60,
    ]
    if question.question_type == "practical":
        lines.append("YECHIM (KOD):")
        lines.append(code or "(kod yo'q)")
    else:
        lines.append("YECHIM (JAVOB):")
        lines.append(note_content or "(javob yo'q)")
    return "\n".join(lines)
