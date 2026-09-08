import random
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.database import get_db
from app.models.models import (
    Challenge, ChallengeDay, Question,
    UserQuestionAssignment, ExamSession,
    ViolationLog, Submission, User
)
from app.schemas.session import (
    EnterDayResponse, TypingStartRequest, AutosaveRequest,
    ViolationRequest, ViolationResponse,
    SubmitRequest, SubmitResponse,
    ChallengeProgressResponse, MyDayStatus
)
from app.core.security import get_current_user
from app.services.sandbox_service import run_code_in_sandbox

router = APIRouter(prefix="/api/v1", tags=["Session"])


# ─── Challengelar ro'yxati ────────────────────────────────────

@router.get("/challenges")
async def list_active_challenges(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Challenge).where(Challenge.status == "active").order_by(Challenge.start_date)
    )
    challenges = result.scalars().all()
    now = datetime.now(timezone.utc)
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "total_days": c.total_days,
            "start_date": c.start_date,
            "end_date": c.start_date + timedelta(days=c.total_days),
            "prize_info": c.prize_info,
            "is_started": c.start_date <= now,
        }
        for c in challenges
    ]


# ─── Challenge progressi (foydalanuvchi uchun) ───────────────

@router.get("/challenges/{challenge_id}/my-progress", response_model=ChallengeProgressResponse)
async def my_progress(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

    now = datetime.now(timezone.utc)
    today = now.date()

    day_statuses = []
    total_my_score = 0

    for day in days:
        day_date = (challenge.start_date + timedelta(days=day.day_number - 1)).date()
        opens_on = day_date.isoformat()
        is_today = day_date == today
        is_locked = day_date > today
        is_expired_no_attempt = day_date < today

        # Bu kun uchun submission bormi?
        sub_q = await db.execute(
            select(Submission)
            .join(ExamSession, Submission.session_id == ExamSession.id)
            .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
            .where(
                UserQuestionAssignment.user_id == current_user.id,
                UserQuestionAssignment.challenge_day_id == day.id
            )
            .order_by(Submission.submitted_at.desc())
        )
        submission = sub_q.scalar_one_or_none()

        # Session bormi?
        sess_q = await db.execute(
            select(ExamSession)
            .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
            .where(
                UserQuestionAssignment.user_id == current_user.id,
                UserQuestionAssignment.challenge_day_id == day.id
            )
        )
        session = sess_q.scalar_one_or_none()

        is_completed = submission is not None
        is_disqualified = session is not None and session.status == "disqualified"

        # Ball faqat ertasi kundan boshlab ko'rinadi
        show_score = day_date < today
        score = submission.score if (submission and show_score) else None
        if score:
            total_my_score += score

        day_statuses.append(MyDayStatus(
            day_id=str(day.id),
            day_number=day.day_number,
            title=day.title,
            time_limit_secs=day.time_limit_secs,
            is_today=is_today,
            is_locked=is_locked,
            is_expired=is_expired_no_attempt and not is_completed and not is_disqualified,
            is_completed=is_completed,
            is_disqualified=is_disqualified,
            score=score,
            opens_on=opens_on,
        ))

    return ChallengeProgressResponse(
        challenge_id=str(challenge.id),
        challenge_name=challenge.name,
        total_days=challenge.total_days,
        days=day_statuses,
        my_total_score=total_my_score if challenge.status == "ended" else None,
    )


# ─── Kunga kirish: random savol tayinlash ────────────────────

@router.post("/days/{day_id}/enter", response_model=EnterDayResponse)
async def enter_day(
    day_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Kun mavjudligini va bugun ekanligini tekshirish
    day = None
    try:
        uuid_obj = uuid.UUID(day_id)
        day_result = await db.execute(select(ChallengeDay).where(ChallengeDay.id == uuid_obj))
        day = day_result.scalar_one_or_none()
    except (ValueError, TypeError):
        if "_day" in str(day_id):
            parts = str(day_id).split("_day")
            try:
                ch_uuid = uuid.UUID(parts[0])
                d_num = int(parts[1])
                day_result = await db.execute(
                    select(ChallengeDay).where(
                        ChallengeDay.challenge_id == ch_uuid,
                        ChallengeDay.day_number == d_num
                    )
                )
                day = day_result.scalar_one_or_none()
            except (ValueError, TypeError):
                pass

    if not day:
        raise HTTPException(status_code=404, detail="Kun topilmadi")

    ch_result = await db.execute(select(Challenge).where(Challenge.id == day.challenge_id))
    challenge = ch_result.scalar_one_or_none()
    if challenge.status != "active":
        raise HTTPException(status_code=400, detail="Bu challenge hozir faol emas")

    now = datetime.now(timezone.utc)
    day_date = (challenge.start_date + timedelta(days=day.day_number - 1)).date()
    today = now.date()

    if day_date > today:
        raise HTTPException(status_code=403, detail=f"Bu kun hali ochilmagan. {day_date.isoformat()} kuni ochiladi")
    if day_date < today:
        raise HTTPException(status_code=403, detail="Bu kunning muddati o'tgan")

    # 1. Tayinlov bor/yo'qligini tekshirish
    assign_result = await db.execute(
        select(UserQuestionAssignment).where(
            UserQuestionAssignment.user_id == current_user.id,
            UserQuestionAssignment.challenge_day_id == day.id
        )
    )
    assignment = assign_result.scalar_one_or_none()

    if not assignment:
        # Random savol tayinlash
        q_result = await db.execute(
            select(Question).where(Question.challenge_day_id == day.id)
        )
        questions = q_result.scalars().all()
        if not questions:
            raise HTTPException(status_code=404, detail="Bu kun uchun savol qo'shilmagan")

        chosen = random.choice(questions)
        assignment = UserQuestionAssignment(
            user_id=current_user.id,
            challenge_day_id=day.id,
            question_id=chosen.id
        )
        db.add(assignment)
        await db.flush()  # ID olish uchun

    # Savolni olish
    q_res = await db.execute(select(Question).where(Question.id == assignment.question_id))
    question = q_res.scalar_one()

    # 2. Faol sessiya bor/yo'qligini tekshirish
    sess_result = await db.execute(
        select(ExamSession).where(
            ExamSession.assignment_id == assignment.id
        )
    )
    session = sess_result.scalar_one_or_none()

    if session:
        # Sessiya diskvalifikatsiya yoki yuborilgan bo'lsa → readonly
        if session.status in ("disqualified", "submitted", "auto_submitted"):
            sub_res = await db.execute(
                select(Submission).where(Submission.session_id == session.id)
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
                question_svg=question.body_svg,
                starter_code=question.starter_code or "",
                time_limit_secs=day.time_limit_secs,
                is_readonly=True,
                previous_code=session.final_code,
                previous_score=submission.score if submission else 0,
            )

        # Vaqt tugaganini tekshirish
        if session.expires_at < now:
            # Avto-submit
            if session.final_code:
                await _do_submit(session, question, session.final_code, db, current_user.id, day_id)
            session.status = "expired" if not session.final_code else "auto_submitted"
            await db.commit()
            return EnterDayResponse(
                session_id=str(session.id),
                expires_at=session.expires_at,
                entered_at=session.entered_at,
                question_id=str(question.id),
                question_title=question.title,
                question_svg=question.body_svg,
                starter_code=question.starter_code or "",
                time_limit_secs=day.time_limit_secs,
                is_readonly=True,
                previous_code=session.final_code,
                previous_score=0,
            )
    else:
        # Yangi sessiya yaratish
        expires_at = now + timedelta(seconds=day.time_limit_secs)
        session = ExamSession(
            user_id=current_user.id,
            assignment_id=assignment.id,
            expires_at=expires_at,
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
        question_svg=question.body_svg,
        starter_code=question.starter_code or "",
        time_limit_secs=day.time_limit_secs,
        is_readonly=False,
    )


# ─── Birinchi klavish vaqti ────────────────────────────────────

@router.patch("/sessions/{session_id}/typing-start")
async def typing_start(
    session_id: str,
    data: TypingStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = await _get_active_session(session_id, current_user.id, db)
    if session.typing_started_at is None:
        session.typing_started_at = data.timestamp
        await db.commit()
    return {"ok": True}


# ─── Avto-saqlash ─────────────────────────────────────────────

@router.patch("/sessions/{session_id}/autosave")
async def autosave(
    session_id: str,
    data: AutosaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = await _get_active_session(session_id, current_user.id, db)
    session.final_code = data.code
    await db.commit()
    return {"ok": True, "saved_at": datetime.now(timezone.utc)}


# ─── Buzilish qayd etish ──────────────────────────────────────

@router.post("/sessions/{session_id}/violation", response_model=ViolationResponse)
async def report_violation(
    session_id: str,
    data: ViolationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = await _get_active_session(session_id, current_user.id, db)

    # Buzilishni log ga yozish
    log = ViolationLog(session_id=session.id, violation_type=data.violation_type)
    db.add(log)

    session.violations_count += 1

    # Challenge max_violations olish
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
        )
    )


# ─── Kod yuborish ─────────────────────────────────────────────

@router.post("/sessions/{session_id}/submit", response_model=SubmitResponse)
async def submit_code(
    session_id: str,
    data: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = await _get_active_session(session_id, current_user.id, db)

    # Vaqt tekshiruvi (3 soniya buffer)
    now = datetime.now(timezone.utc)
    if session.expires_at < now - timedelta(seconds=3):
        session.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Vaqt tugagan. Kod yuborilmadi.")

    # Savolni olish
    assign_res = await db.execute(
        select(UserQuestionAssignment).where(UserQuestionAssignment.id == session.assignment_id)
    )
    assignment = assign_res.scalar_one()
    question = await db.execute(select(Question).where(Question.id == assignment.question_id))
    question = question.scalar_one()
    day = await db.execute(select(ChallengeDay).where(ChallengeDay.id == assignment.challenge_day_id))
    day = day.scalar_one()

    # Docker sandbox da kodni baholash
    result = await run_code_in_sandbox(data.code, question.test_cases)

    # Ball hisoblash (10 ballik tizim)
    passed = result.get("passed", 0)
    total = result.get("total", 1)
    score = round((passed / total) * 10) if total > 0 else 0

    # Submission yozish
    submission = Submission(
        session_id=session.id,
        user_id=current_user.id,
        challenge_day_id=day.id,
        code=data.code,
        result=result.get("status", "error"),
        score=score,
        execution_ms=result.get("execution_ms"),
        docker_output=result.get("output"),
    )
    db.add(submission)

    # Sessiyani yakunlash
    session.status = "submitted"
    session.submitted_at = now
    session.final_code = data.code
    session.is_readonly = True

    # Foydalanuvchi umumiy balini yangilash
    user_res = await db.execute(select(User).where(User.id == current_user.id))
    user = user_res.scalar_one()
    user.total_score += score

    await db.commit()

    return SubmitResponse(
        result=result.get("status", "error"),
        score=score,
        execution_ms=result.get("execution_ms"),
        output=result.get("output"),
        message=f"Natija: {score}/10 ball ({passed}/{total} test muvaffaqiyatli)"
    )


# ─── Helpers ──────────────────────────────────────────────────

async def _get_active_session(session_id: str, user_id, db: AsyncSession) -> ExamSession:
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.id == session_id,
            ExamSession.user_id == user_id,
            ExamSession.status == "active"
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Faol sessiya topilmadi")
    return session


async def _do_submit(session: ExamSession, question: Question, code: str, db: AsyncSession, user_id, day_id):
    result = await run_code_in_sandbox(code, question.test_cases)
    passed = result.get("passed", 0)
    total = result.get("total", 1)
    score = round((passed / total) * 10) if total > 0 else 0

    submission = Submission(
        session_id=session.id,
        user_id=user_id,
        challenge_day_id=day_id,
        code=code,
        result=result.get("status", "error"),
        score=score,
        execution_ms=result.get("execution_ms"),
        docker_output=result.get("output"),
    )
    db.add(submission)

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if user:
        user.total_score += score
