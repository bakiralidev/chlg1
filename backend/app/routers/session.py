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
    ChallengeProgressResponse, MyDayStatus,
    RunCodeRequest, RunCodeResponse
)
from app.services.sandbox_service import execute_python_code
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Session"])


# --- Challengelar royxati ------------------------------------

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


# --- Challenge progressi ------------------------------------

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

        # Bajarilgan bo'lsa ballni ko'rsatish
        score = submission.score if submission else None
        if score:
            total_my_score += score

        # O'tgan kunlar ham ochiq bo'ladi (faqat topshirilgan yoki diskvalifikatsiya bo'lmasa)
        is_expired = False

        day_statuses.append(MyDayStatus(
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
        ))

    return ChallengeProgressResponse(
        challenge_id=str(challenge.id),
        challenge_name=challenge.name,
        total_days=challenge.total_days,
        days=day_statuses,
        my_total_score=total_my_score if challenge.status == "ended" else None,
    )


# --- Kunga kirish: random savol tayinlash --------------------

@router.post("/days/{day_id}/enter", response_model=EnterDayResponse)
async def enter_day(
    day_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    if challenge.status != "active":
        raise HTTPException(status_code=400, detail="Bu challenge hozir faol emas")

    now = datetime.now(timezone.utc)
    day_date = (challenge.start_date + timedelta(days=day.day_number - 1)).date()
    today = now.date()

    if day_date > today:
        raise HTTPException(status_code=403, detail=f"Bu kun hali ochilmagan. {day_date.isoformat()} kuni ochiladi")
    # O'tgan kunlarni ham ishlab ko'rishga ruxsat etiladi

    # Tayinlov bor/yoqligini tekshirish
    assign_result = await db.execute(
        select(UserQuestionAssignment).where(
            UserQuestionAssignment.user_id == current_user.id,
            UserQuestionAssignment.challenge_day_id == day.id
        )
    )
    assignment = assign_result.scalar_one_or_none()

    if not assignment:
        # Random savol tayinlash (takrorlanmas va teng taqsimlash)
        q_result = await db.execute(
            select(Question).where(Question.challenge_day_id == day.id)
        )
        questions = q_result.scalars().all()
        if not questions:
            raise HTTPException(status_code=404, detail="Bu kun uchun savol qoshilmagan")

        # Har bir savol bu kunda necha marta tayinlanganini hisoblash
        counts_res = await db.execute(
            select(
                UserQuestionAssignment.question_id,
                func.count(UserQuestionAssignment.id)
            )
            .where(UserQuestionAssignment.challenge_day_id == day.id)
            .group_by(UserQuestionAssignment.question_id)
        )
        assigned_counts = dict(counts_res.all())

        # Eng kam tayinlangan savollar hovuzidan tasodifiy tanlash
        min_count = min(assigned_counts.get(q.id, 0) for q in questions)
        least_assigned_questions = [
            q for q in questions if assigned_counts.get(q.id, 0) == min_count
        ]
        chosen = random.choice(least_assigned_questions)
        assignment = UserQuestionAssignment(
            user_id=current_user.id,
            challenge_day_id=day.id,
            question_id=chosen.id
        )
        db.add(assignment)
        await db.flush()

    # Savolni olish
    q_res = await db.execute(select(Question).where(Question.id == assignment.question_id))
    question = q_res.scalar_one()

    # Faol sessiya bor/yoqligini tekshirish
    sess_result = await db.execute(
        select(ExamSession).where(ExamSession.assignment_id == assignment.id)
    )
    session = sess_result.scalar_one_or_none()

    if session:
        # Yuborilgan yoki diskvalifikatsiya
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
                question_type=question.question_type,
                question_body=question.body_text,
                starter_code=question.starter_code or "",
                time_limit_secs=day.time_limit_secs,
                is_readonly=True,
                previous_code=session.final_code,
                previous_note=session.note_content,
                previous_score=submission.score if submission else 0,
                violations_count=session.violations_count,
                max_violations=challenge.max_violations,
            )

        # Vaqt tugaganini tekshirish
        if session.expires_at < now:
            sub_check = await db.execute(
                select(Submission).where(Submission.session_id == session.id)
            )
            sub_exists = sub_check.scalar_one_or_none()
            if not sub_exists:
                # Oldin yuborilmagan bo'lsa, o'tgan kunni ishlash uchun yangi vaqt berish
                session.expires_at = now + timedelta(seconds=day.time_limit_secs)
                session.status = "active"
                session.violations_count = 0
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
                    time_limit_secs=day.time_limit_secs,
                    is_readonly=False,
                    previous_code=session.final_code,
                    previous_note=session.note_content,
                    violations_count=0,
                    max_violations=challenge.max_violations,
                )
            else:
                session.status = "submitted"
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
                    time_limit_secs=day.time_limit_secs,
                    is_readonly=True,
                    previous_code=session.final_code,
                    previous_note=session.note_content,
                    previous_score=sub_exists.score if sub_exists else 0,
                    violations_count=session.violations_count,
                    max_violations=challenge.max_violations,
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
        question_type=question.question_type,
        question_body=question.body_text,
        starter_code=question.starter_code or "",
        time_limit_secs=day.time_limit_secs,
        is_readonly=False,
        previous_code=session.final_code,
        previous_note=session.note_content,
        violations_count=session.violations_count,
        max_violations=challenge.max_violations,
    )


# --- Birinchi klavish vaqti ------------------------------------

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


# --- Avto-saqlash ---------------------------------------------

@router.patch("/sessions/{session_id}/autosave")
async def autosave(
    session_id: str,
    data: AutosaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = await _get_active_session(session_id, current_user.id, db)
    if data.code is not None:
        session.final_code = data.code
    if data.note_content is not None:
        session.note_content = data.note_content
    await db.commit()
    return {"ok": True, "saved_at": datetime.now(timezone.utc)}


# --- Buzilish qayd etish --------------------------------------

@router.post("/sessions/{session_id}/violation", response_model=ViolationResponse)
async def report_violation(
    session_id: str,
    data: ViolationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        )
    )


# --- Kodni Terminalda ishga tushirish ------------------------

@router.post("/sessions/{session_id}/run", response_model=RunCodeResponse)
async def run_session_code(
    session_id: str,
    data: RunCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Sessiyani tekshirish (foydalanuvchiga tegishlimi)
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.id == session_id,
            ExamSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    exec_result = await execute_python_code(
        code=data.code,
        input_data=data.input_data or "",
        timeout_seconds=5.0
    )

    return RunCodeResponse(
        stdout=exec_result["stdout"],
        stderr=exec_result["stderr"],
        exit_code=exec_result["exit_code"],
        execution_ms=exec_result["execution_ms"]
    )


# --- Kod/Note yuborish ----------------------------------------

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
    question_res = await db.execute(select(Question).where(Question.id == assignment.question_id))
    question = question_res.scalar_one()
    day_res = await db.execute(select(ChallengeDay).where(ChallengeDay.id == assignment.challenge_day_id))
    day = day_res.scalar_one()

    # Sarflangan vaqt hisoblash
    time_spent = None
    if session.typing_started_at:
        delta = now - session.typing_started_at
        time_spent = int(delta.total_seconds())

    # Fayl mazmunini shakllantirish
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

    # Submission yozish  -  Docker yo'q, manual_review
    submission = Submission(
        session_id=session.id,
        user_id=current_user.id,
        challenge_day_id=day.id,
        submission_type=question.question_type,
        code=data.code,
        note_content=data.note_content,
        file_content=file_content,
        result="manual_review",  # AI tomonidan baholanadi
        score=0,  # Excel import bilan keyinroq to'ldiriladi
    )
    db.add(submission)

    # Sessiyani yakunlash
    session.status = "submitted"
    session.submitted_at = now
    session.final_code = data.code
    session.note_content = data.note_content
    session.time_spent_secs = time_spent
    session.is_readonly = True

    await db.commit()

    return SubmitResponse(
        result="submitted",
        score=0,
        message="Yechimingiz muvaffaqiyatli qabul qilindi. Natija AI baholashidan keyin e'lon qilinadi."
    )


# --- Helpers --------------------------------------------------

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


async def _do_auto_submit(session: ExamSession, question: Question, db: AsyncSession, user_id, day_id):
    """Vaqt tugaganda avtomatik yechim saqlash."""
    now = datetime.now(timezone.utc)
    time_spent = None
    if session.typing_started_at:
        delta = now - session.typing_started_at
        time_spent = int(delta.total_seconds())

    file_content = (
        f"AVTOMATIK SUBMIT (Vaqt tugadi)\n"
        f"Savol: {question.title}\n"
        f"Tur: {question.question_type}\n"
        f"{'=' * 60}\n"
    )
    if question.question_type == "practical":
        file_content += f"KOD:\n{session.final_code or '(kod yozilmagan)'}"
    else:
        file_content += f"JAVOB:\n{session.note_content or '(javob yozilmagan)'}"

    submission = Submission(
        session_id=session.id,
        user_id=user_id,
        challenge_day_id=day_id,
        submission_type=question.question_type,
        code=session.final_code,
        note_content=session.note_content,
        file_content=file_content,
        result="auto_submitted",
        score=0,
    )
    db.add(submission)
    session.time_spent_secs = time_spent
    session.submitted_at = now


def _build_submission_file(question, day, user, session, code, note_content, submitted_at, time_spent) -> str:
    """Yuborilgan yechim uchun fayl mazmunini yaratish."""
    lines = [
        f"PYCHALLENGE SUBMISSION",
        f"{'=' * 60}",
        f"FOYDALANUVCHI: {user.username} ({user.email})",
        f"KUN: Day {day.day_number}  -  {day.title or ''}",
        f"SAVOL: {question.title}",
        f"SAVOL TURI: {'Amaliy (Practical)' if question.question_type == 'practical' else 'Nazariy (Theoretical)'}",
        f"QIYINLIK: {question.difficulty}",
        f"{'=' * 60}",
        f"SAVOL MATNI:",
        question.body_text,
        f"{'=' * 60}",
        f"SESSIYAGA KIRISH: {session.entered_at}",
        f"YOZISHNI BOSHLASH: {session.typing_started_at or 'nomalum'}",
        f"YUBORISH VAQTI: {submitted_at}",
        f"SARFLANGAN VAQT: {time_spent or 'nomalum'} soniya",
        f"QOIDABUZARLIKLAR: {session.violations_count}",
        f"{'=' * 60}",
    ]
    if question.question_type == "practical":
        lines.append("YECHIM (KOD):")
        lines.append(code or "(kod yo'q)")
    else:
        lines.append("YECHIM (JAVOB):")
        lines.append(note_content or "(javob yo'q)")

    return "\n".join(lines)
