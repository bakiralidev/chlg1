from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import io
import zipfile
import openpyxl

from app.db.database import get_db
from app.models.models import (
    Challenge, ChallengeDay, Question, ExamSession,
    Submission, User, UserQuestionAssignment, ParticipantAIScore, ViolationLog
)
from app.schemas.admin import (
    ChallengeCreate, ChallengeResponse,
    DayCreate, DayResponse,
    QuestionCreate, QuestionResponse,
    ChallengeStats, AIScoreImportResult, GradeRequest
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# --- CHALLENGES -----------------------------------------------

@router.post("/challenges", response_model=ChallengeResponse, status_code=201)
async def create_challenge(
    data: ChallengeCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    challenge = Challenge(**data.model_dump(), created_by=admin.id)
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return _challenge_to_dict(challenge)


@router.get("/challenges", response_model=list[ChallengeResponse])
async def list_challenges(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(Challenge).order_by(Challenge.created_at.desc()))
    return [_challenge_to_dict(c) for c in result.scalars().all()]


@router.get("/challenges/{challenge_id}", response_model=ChallengeResponse)
async def get_challenge(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")
    return _challenge_to_dict(challenge)


@router.delete("/challenges/{challenge_id}")
async def delete_challenge(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")
    await db.delete(challenge)
    await db.commit()
    return {"message": "Challenge ochirildi"}


@router.put("/challenges/{challenge_id}", response_model=ChallengeResponse)
async def update_challenge(
    challenge_id: str,
    data: ChallengeCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")
    if challenge.status == "ended":
        raise HTTPException(status_code=400, detail="Tugagan challengeni ozgartirish mumkin emas")

    for key, value in data.model_dump().items():
        setattr(challenge, key, value)
    await db.commit()
    await db.refresh(challenge)
    return _challenge_to_dict(challenge)


@router.post("/challenges/{challenge_id}/activate")
async def activate_challenge(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    days = await db.execute(
        select(func.count()).where(ChallengeDay.challenge_id == challenge_id)
    )
    if days.scalar() == 0:
        raise HTTPException(status_code=400, detail="Challengeda hech qanday kun yoq")

    challenge.status = "active"
    await db.commit()
    return {"message": f"'{challenge.name}' challenge faollashtirildi"}


@router.get("/challenges/{challenge_id}/stats", response_model=ChallengeStats)
async def challenge_stats(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    participants = await db.execute(
        select(func.count(ExamSession.user_id.distinct())).where(
            ExamSession.assignment_id.in_(
                select(UserQuestionAssignment.id).where(
                    UserQuestionAssignment.challenge_day_id.in_(
                        select(ChallengeDay.id).where(ChallengeDay.challenge_id == challenge_id)
                    )
                )
            )
        )
    )
    submissions = await db.execute(
        select(func.count(Submission.id)).where(
            Submission.challenge_day_id.in_(
                select(ChallengeDay.id).where(ChallengeDay.challenge_id == challenge_id)
            )
        )
    )
    days_with_q = await db.execute(
        select(func.count(ChallengeDay.id.distinct())).where(
            ChallengeDay.challenge_id == challenge_id,
            ChallengeDay.id.in_(select(Question.challenge_day_id))
        )
    )
    return ChallengeStats(
        challenge_id=challenge_id,
        total_participants=participants.scalar() or 0,
        total_submissions=submissions.scalar() or 0,
        days_with_questions=days_with_q.scalar() or 0,
    )


# --- ZIP EXPORT -----------------------------------------------

@router.get("/challenges/{challenge_id}/export-zip")
async def export_submissions_zip(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Barcha ishtirokchilarning yechimlarini ZIP arxivi sifatida yuklab berish."""
    challenge_res = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = challenge_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    # Barcha submissionlarni foydalanuvchi va kun ma'lumotlari bilan olish
    result = await db.execute(
        select(
            Submission,
            User.username,
            User.email,
            ChallengeDay.day_number,
            ChallengeDay.title.label("day_title"),
            Question.title.label("question_title"),
            Question.question_type,
            ExamSession.entered_at,
            ExamSession.typing_started_at,
            ExamSession.submitted_at,
            ExamSession.time_spent_secs,
            ExamSession.violations_count,
            ExamSession.status.label("session_status"),
        )
        .join(User, Submission.user_id == User.id)
        .join(ChallengeDay, Submission.challenge_day_id == ChallengeDay.id)
        .join(ExamSession, Submission.session_id == ExamSession.id)
        .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
        .join(Question, UserQuestionAssignment.question_id == Question.id)
        .where(ChallengeDay.challenge_id == challenge_id)
        .order_by(User.username, ChallengeDay.day_number)
    )
    rows = result.all()

    # ZIP yaratish (xotirada)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            sub = row.Submission
            username = row.username.replace(" ", "_")
            day_folder = f"Day_{row.day_number:02d}"
            safe_title = (row.question_title or "savol").replace("/", "_").replace(" ", "_")
            ext = ".py" if row.question_type == "practical" else ".txt"
            filename = f"{username}/{day_folder}/{safe_title}{ext}"

            # Fayl mazmuni
            if sub.file_content:
                content = sub.file_content
            else:
                # Eski yozuvlar uchun fallback
                content = _build_file_content(row)

            zf.writestr(filename, content)

        # Metadata CSV
        meta_lines = ["email,username,day,status,time_spent_secs,violations,score,submitted_at"]
        for row in rows:
            sub = row.Submission
            meta_lines.append(
                f"{row.email},{row.username},{row.day_number},"
                f"{row.session_status},{row.time_spent_secs or 0},"
                f"{row.violations_count},{sub.score},"
                f"{sub.submitted_at}"
            )
        zf.writestr("_metadata.csv", "\n".join(meta_lines))

    zip_buffer.seek(0)
    safe_name = challenge.name.replace(" ", "_")
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_submissions.zip"'}
    )


def _build_file_content(row) -> str:
    """Eski submission uchun fayl mazmunini qayta yaratish."""
    sub = row.Submission
    lines = [
        f"CHALLENGE: {row.day_title or f'Day {row.day_number}'}",
        f"SAVOL: {row.question_title}",
        f"TUR: {row.question_type}",
        f"FOYDALANUVCHI: {row.username} ({row.email})",
        f"SESSIYAGA KIRISH: {row.entered_at}",
        f"YOZISHNI BOSHLASH: {row.typing_started_at}",
        f"YUBORISH VAQTI: {sub.submitted_at}",
        f"SARFLANGAN VAQT: {row.time_spent_secs or 'nomalum'} soniya",
        f"QOIDABUZARLIKLAR: {row.violations_count}",
        "=" * 60,
    ]
    if row.question_type == "practical":
        lines.append("KOD:")
        lines.append(sub.code or "(kod yuborilmagan)")
    else:
        lines.append("JAVOB:")
        lines.append(sub.note_content or "(javob yuborilmagan)")
    return "\n".join(lines)


# --- EXCEL AI SCORE IMPORT ------------------------------------

@router.post("/challenges/{challenge_id}/import-scores", response_model=AIScoreImportResult)
async def import_ai_scores(
    challenge_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Excel faylidan AI baholash natijalarini import qilish.
    Excel ustunlari: email | day_number | approach | correctness | speed | logic | memory | notes
    """
    challenge_res = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    if not challenge_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Faqat .xlsx yoki .xls fayl qabul qilinadi")

    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active

    CATEGORIES = ["approach", "correctness", "speed", "logic", "memory"]
    total_rows = 0
    matched_users = set()
    imported_scores = 0
    skipped = 0
    errors = []

    # Sarlavha qatori
    headers = [str(cell.value).strip().lower() if cell.value else "" for cell in ws[1]]

    def col(name):
        try:
            return headers.index(name)
        except ValueError:
            return None

    email_col = col("email")
    day_col = col("day_number")

    if email_col is None:
        raise HTTPException(status_code=400, detail="Excel da 'email' ustuni topilmadi")

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not any(row):
            continue
        total_rows += 1

        email = str(row[email_col]).strip() if row[email_col] else None
        if not email:
            errors.append(f"Qator {row_num}: email bo'sh")
            skipped += 1
            continue

        # Foydalanuvchini topish
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalar_one_or_none()
        if not user:
            errors.append(f"Qator {row_num}: '{email}' foydalanuvchi topilmadi")
            skipped += 1
            continue

        matched_users.add(user.id)

        # Kun ID ni topish
        day_id = None
        if day_col is not None and row[day_col]:
            try:
                day_number = int(row[day_col])
                day_res = await db.execute(
                    select(ChallengeDay).where(
                        ChallengeDay.challenge_id == challenge_id,
                        ChallengeDay.day_number == day_number
                    )
                )
                day = day_res.scalar_one_or_none()
                if day:
                    day_id = day.id
            except (ValueError, TypeError):
                pass

        # Har bir kategoriya uchun ball saqlash
        notes_col = col("notes")
        notes_val = str(row[notes_col]).strip() if (notes_col is not None and row[notes_col]) else None

        for cat in CATEGORIES:
            cat_col = col(cat)
            if cat_col is None:
                continue
            score_val = row[cat_col]
            if score_val is None:
                continue
            try:
                score_int = int(score_val)
                if not (0 <= score_int <= 10):
                    errors.append(f"Qator {row_num}, {cat}: ball 0-10 oraligida bolishi kerak")
                    continue
            except (ValueError, TypeError):
                errors.append(f"Qator {row_num}, {cat}: yaroqsiz qiymat '{score_val}'")
                continue

            # Upsert (ON CONFLICT UPDATE)
            existing = await db.execute(
                select(ParticipantAIScore).where(
                    ParticipantAIScore.challenge_id == challenge_id,
                    ParticipantAIScore.user_id == user.id,
                    ParticipantAIScore.day_id == day_id,
                    ParticipantAIScore.category == cat
                )
            )
            existing_score = existing.scalar_one_or_none()
            if existing_score:
                existing_score.score = score_int
                existing_score.notes = notes_val
            else:
                new_score = ParticipantAIScore(
                    challenge_id=challenge_id,
                    user_id=user.id,
                    day_id=day_id,
                    category=cat,
                    score=score_int,
                    notes=notes_val
                )
                db.add(new_score)
            imported_scores += 1

    await db.commit()

    return AIScoreImportResult(
        total_rows=total_rows,
        matched_users=len(matched_users),
        imported_scores=imported_scores,
        skipped=skipped,
        errors=errors[:20]  # Maksimal 20 ta xatolik ko'rsatish
    )


# --- DAYS -----------------------------------------------------

@router.post("/days", response_model=DayResponse, status_code=201)
async def create_day(
    data: DayCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    ch = await db.execute(select(Challenge).where(Challenge.id == data.challenge_id))
    if not ch.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    day = ChallengeDay(**data.model_dump())
    db.add(day)
    await db.commit()
    await db.refresh(day)
    return _day_to_dict(day)


@router.get("/challenges/{challenge_id}/days", response_model=list[DayResponse])
async def list_days(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(
        select(ChallengeDay)
        .where(ChallengeDay.challenge_id == challenge_id)
        .order_by(ChallengeDay.day_number)
    )
    return [_day_to_dict(d) for d in result.scalars().all()]


@router.put("/days/{day_id}", response_model=DayResponse)
async def update_day(
    day_id: str,
    data: DayCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(ChallengeDay).where(ChallengeDay.id == day_id))
    day = result.scalar_one_or_none()
    if not day:
        raise HTTPException(status_code=404, detail="Kun topilmadi")
    for key, value in data.model_dump().items():
        setattr(day, key, value)
    await db.commit()
    await db.refresh(day)
    return _day_to_dict(day)


@router.delete("/days/{day_id}")
async def delete_day(
    day_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(ChallengeDay).where(ChallengeDay.id == day_id))
    day = result.scalar_one_or_none()
    if not day:
        raise HTTPException(status_code=404, detail="Kun topilmadi")
    await db.delete(day)
    await db.commit()
    return {"message": "Kun ochirildi"}


# --- QUESTIONS ------------------------------------------------

@router.post("/questions", response_model=QuestionResponse, status_code=201)
async def create_question(
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    day = await db.execute(select(ChallengeDay).where(ChallengeDay.id == data.challenge_day_id))
    if not day.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Kun topilmadi")

    payload = data.model_dump()
    if payload.get("test_cases"):
        payload["test_cases"] = [tc for tc in payload["test_cases"]]
    else:
        payload["test_cases"] = None

    question = Question(**payload)
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return _question_to_dict(question)


@router.get("/days/{day_id}/questions", response_model=list[QuestionResponse])
async def list_questions(
    day_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(
        select(Question).where(Question.challenge_day_id == day_id)
    )
    return [_question_to_dict(q) for q in result.scalars().all()]


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Savol topilmadi")
    await db.delete(question)
    await db.commit()
    return {"message": "Savol ochirildi"}


@router.get("/challenges/{challenge_id}/questions")
async def list_challenge_questions(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(
        select(Question, ChallengeDay.day_number, ChallengeDay.title.label("day_title"))
        .join(ChallengeDay, Question.challenge_day_id == ChallengeDay.id)
        .where(ChallengeDay.challenge_id == challenge_id)
        .order_by(ChallengeDay.day_number, Question.created_at)
    )
    rows = result.all()
    return [
        {
            "id": str(r.Question.id),
            "challenge_day_id": str(r.Question.challenge_day_id),
            "day_number": r.day_number,
            "day_title": r.day_title,
            "title": r.Question.title,
            "question_type": r.Question.question_type,
            "difficulty": r.Question.difficulty,
            "starter_code": r.Question.starter_code,
            "created_at": r.Question.created_at,
        }
        for r in rows
    ]


# --- AI SCORES LEADERBOARD ------------------------------------

@router.get("/challenges/{challenge_id}/ai-scores")
async def get_ai_scores(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Challenge ishtirokchilarining AI baholash natijalari."""
    result = await db.execute(
        select(
            ParticipantAIScore,
            User.username,
            User.email,
            ChallengeDay.day_number
        )
        .join(User, ParticipantAIScore.user_id == User.id)
        .outerjoin(ChallengeDay, ParticipantAIScore.day_id == ChallengeDay.id)
        .where(ParticipantAIScore.challenge_id == challenge_id)
        .order_by(User.username, ChallengeDay.day_number, ParticipantAIScore.category)
    )
    rows = result.all()

    # Foydalanuvchi bo'yicha guruhlashtirish
    users_data = {}
    for row in rows:
        uid = str(row.ParticipantAIScore.user_id)
        if uid not in users_data:
            users_data[uid] = {
                "user_id": uid,
                "username": row.username,
                "email": row.email,
                "total_score": 0,
                "days": {}
            }
        day_key = str(row.day_number) if row.day_number else "overall"
        if day_key not in users_data[uid]["days"]:
            users_data[uid]["days"][day_key] = {}
        users_data[uid]["days"][day_key][row.ParticipantAIScore.category] = {
            "score": row.ParticipantAIScore.score,
            "notes": row.ParticipantAIScore.notes
        }
        users_data[uid]["total_score"] += row.ParticipantAIScore.score

    leaderboard = sorted(users_data.values(), key=lambda x: x["total_score"], reverse=True)
    return leaderboard


# --- Helpers --------------------------------------------------

def _challenge_to_dict(c: Challenge) -> dict:
    return {
        "id": str(c.id), "name": c.name, "description": c.description,
        "total_days": c.total_days, "start_date": c.start_date,
        "prize_info": c.prize_info, "status": c.status,
        "max_violations": c.max_violations, "created_at": c.created_at,
    }

def _day_to_dict(d: ChallengeDay) -> dict:
    return {
        "id": str(d.id), "challenge_id": str(d.challenge_id),
        "day_number": d.day_number, "title": d.title,
        "time_limit_secs": d.time_limit_secs,
    }

def _question_to_dict(q: Question) -> dict:
    return {
        "id": str(q.id), "challenge_day_id": str(q.challenge_day_id),
        "title": q.title, "question_type": q.question_type,
        "difficulty": q.difficulty, "created_at": q.created_at,
    }


# --- PARTICIPANTS MANAGEMENT ---------------------------------

@router.get("/participants")
async def list_participants(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Barcha qatnashuvchilar (oddiy foydalanuvchilar) ro'yxati va ularning statistikasi."""
    query = select(User).where(User.is_admin == False).order_by(User.created_at.desc())
    if search:
        search_filter = f"%{search}%".lower()
        query = query.where(
            (func.lower(User.username).ilike(search_filter)) |
            (func.lower(User.email).ilike(search_filter))
        )
    result = await db.execute(query)
    users = result.scalars().all()

    participants = []
    for u in users:
        subs_res = await db.execute(
            select(func.count(Submission.id), func.sum(Submission.score))
            .where(Submission.user_id == u.id)
        )
        subs_count, total_score = subs_res.first()

        dq_res = await db.execute(
            select(func.count(ExamSession.id))
            .where(ExamSession.user_id == u.id, ExamSession.status == "disqualified")
        )
        dq_count = dq_res.scalar() or 0

        last_sub_res = await db.execute(
            select(Submission.submitted_at)
            .where(Submission.user_id == u.id)
            .order_by(Submission.submitted_at.desc())
            .limit(1)
        )
        last_active = last_sub_res.scalar_one_or_none()

        participants.append({
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "created_at": u.created_at,
            "total_score": int(total_score) if total_score is not None else (u.total_score or 0),
            "submissions_count": subs_count or 0,
            "disqualified_count": dq_count,
            "last_active": last_active or u.created_at,
        })

    return participants


# --- SUBMISSIONS & GRADING ------------------------------------

@router.get("/submissions")
async def list_submissions(
    challenge_id: Optional[str] = None,
    day_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Ishtirokchilar tomonidan yuborilgan yechimlar va sessiyalar ro'yxati."""
    query = (
        select(
            ExamSession,
            Submission,
            User.username,
            User.email,
            ChallengeDay.id.label("c_day_id"),
            ChallengeDay.day_number,
            ChallengeDay.title.label("day_title"),
            Challenge.id.label("challenge_id"),
            Challenge.name.label("challenge_name"),
            Question.title.label("question_title"),
            Question.question_type,
            Question.difficulty,
        )
        .join(User, ExamSession.user_id == User.id)
        .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
        .join(ChallengeDay, UserQuestionAssignment.challenge_day_id == ChallengeDay.id)
        .join(Challenge, ChallengeDay.challenge_id == Challenge.id)
        .join(Question, UserQuestionAssignment.question_id == Question.id)
        .outerjoin(Submission, Submission.session_id == ExamSession.id)
    )

    if challenge_id:
        query = query.where(Challenge.id == challenge_id)
    if day_id:
        query = query.where(ChallengeDay.id == day_id)
    if user_id:
        query = query.where(User.id == user_id)
    if status:
        if status == "disqualified":
            query = query.where(ExamSession.status == "disqualified")
        elif status == "graded":
            query = query.where(Submission.score > 0)
        elif status == "ungraded":
            query = query.where((Submission.score == None) | (Submission.score == 0), ExamSession.status != "disqualified")
        elif status in ("submitted", "auto_submitted", "active"):
            query = query.where(ExamSession.status == status)

    if search:
        search_filter = f"%{search}%".lower()
        query = query.where(
            (func.lower(User.username).ilike(search_filter)) |
            (func.lower(User.email).ilike(search_filter)) |
            (func.lower(Question.title).ilike(search_filter))
        )

    query = query.order_by(ExamSession.submitted_at.desc().nullslast(), ExamSession.entered_at.desc())
    result = await db.execute(query)
    rows = result.all()

    items = []
    for r in rows:
        sess = r.ExamSession
        sub = r.Submission
        items.append({
            "id": str(sub.id) if sub else str(sess.id),
            "session_id": str(sess.id),
            "user": {
                "id": str(sess.user_id),
                "username": r.username,
                "email": r.email,
            },
            "challenge": {
                "id": str(r.challenge_id),
                "name": r.challenge_name,
            },
            "day": {
                "id": str(r.c_day_id),
                "day_number": r.day_number,
                "title": r.day_title,
            },
            "question": {
                "title": r.question_title,
                "question_type": r.question_type,
                "difficulty": r.difficulty,
            },
            "submission_type": sub.submission_type if sub else ("practical" if sess.final_code else "theoretical"),
            "code": sub.code if sub else sess.final_code,
            "note_content": sub.note_content if sub else sess.note_content,
            "score": sub.score if sub else 0,
            "result": sub.result if sub else ("disqualified" if sess.status == "disqualified" else "pending"),
            "submitted_at": sub.submitted_at if sub else sess.submitted_at,
            "entered_at": sess.entered_at,
            "time_spent_secs": sess.time_spent_secs or 0,
            "violations_count": sess.violations_count or 0,
            "session_status": sess.status,
        })
    return items


@router.get("/submissions/{item_id}")
async def get_submission_detail(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Yagona yechimning to'liq detallari: savol sharti, yozilgan javob, qoidabuzarliklar va baholar."""
    sub_res = await db.execute(select(Submission).where(Submission.id == item_id))
    sub = sub_res.scalar_one_or_none()
    sess_id = sub.session_id if sub else item_id

    result = await db.execute(
        select(
            ExamSession,
            Submission,
            User.username,
            User.email,
            ChallengeDay.id.label("c_day_id"),
            ChallengeDay.day_number,
            ChallengeDay.title.label("day_title"),
            Challenge.id.label("challenge_id"),
            Challenge.name.label("challenge_name"),
            Question.id.label("question_id"),
            Question.title.label("question_title"),
            Question.question_type,
            Question.difficulty,
            Question.body_text,
            Question.starter_code,
        )
        .join(User, ExamSession.user_id == User.id)
        .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
        .join(ChallengeDay, UserQuestionAssignment.challenge_day_id == ChallengeDay.id)
        .join(Challenge, ChallengeDay.challenge_id == Challenge.id)
        .join(Question, UserQuestionAssignment.question_id == Question.id)
        .outerjoin(Submission, Submission.session_id == ExamSession.id)
        .where((ExamSession.id == sess_id) | (Submission.id == item_id))
    )
    r = result.first()
    if not r:
        raise HTTPException(status_code=404, detail="Yechim yoki sessiya topilmadi")

    sess = r.ExamSession
    sub = r.Submission

    v_rows = await db.execute(
        select(ViolationLog).where(ViolationLog.session_id == sess.id).order_by(ViolationLog.created_at)
    )
    violations = [
        {"id": v.id, "violation_type": v.violation_type, "created_at": v.created_at}
        for v in v_rows.scalars().all()
    ]

    ai_rows = await db.execute(
        select(ParticipantAIScore).where(
            ParticipantAIScore.user_id == sess.user_id,
            ParticipantAIScore.challenge_id == r.challenge_id
        )
    )
    ai_scores = [
        {"category": s.category, "score": s.score, "notes": s.notes}
        for s in ai_rows.scalars().all()
    ]

    return {
        "id": str(sub.id) if sub else str(sess.id),
        "session_id": str(sess.id),
        "user": {
            "id": str(sess.user_id),
            "username": r.username,
            "email": r.email,
        },
        "challenge": {
            "id": str(r.challenge_id),
            "name": r.challenge_name,
        },
        "day": {
            "id": str(r.c_day_id),
            "day_number": r.day_number,
            "title": r.day_title,
        },
        "question": {
            "id": str(r.question_id),
            "title": r.question_title,
            "question_type": r.question_type,
            "difficulty": r.difficulty,
            "body_text": r.body_text,
            "starter_code": r.starter_code,
        },
        "submission_type": sub.submission_type if sub else ("practical" if sess.final_code else "theoretical"),
        "code": sub.code if sub else sess.final_code,
        "note_content": sub.note_content if sub else sess.note_content,
        "file_content": sub.file_content if sub else None,
        "score": sub.score if sub else 0,
        "result": sub.result if sub else ("disqualified" if sess.status == "disqualified" else "pending"),
        "submitted_at": sub.submitted_at if sub else sess.submitted_at,
        "entered_at": sess.entered_at,
        "typing_started_at": sess.typing_started_at,
        "time_spent_secs": sess.time_spent_secs or 0,
        "violations_count": sess.violations_count or 0,
        "session_status": sess.status,
        "violations": violations,
        "ai_scores": ai_scores,
    }


@router.post("/submissions/{item_id}/grade")
async def grade_submission(
    item_id: str,
    data: GradeRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Ishtirokchi topshirig'ini to'g'ridan-to'g'ri baholash (0-100 ball va izoh)."""
    if data.score < 0 or data.score > 100:
        raise HTTPException(status_code=400, detail="Ball 0 dan 100 gacha bo'lishi kerak")

    sub_res = await db.execute(select(Submission).where(Submission.id == item_id))
    sub = sub_res.scalar_one_or_none()

    if not sub:
        sub_res = await db.execute(select(Submission).where(Submission.session_id == item_id))
        sub = sub_res.scalar_one_or_none()

    if not sub:
        sess_res = await db.execute(select(ExamSession).where(ExamSession.id == item_id))
        sess = sess_res.scalar_one_or_none()
        if not sess:
            raise HTTPException(status_code=404, detail="Yechim yoki sessiya topilmadi")

        assign_res = await db.execute(
            select(UserQuestionAssignment).where(UserQuestionAssignment.id == sess.assignment_id)
        )
        assignment = assign_res.scalar_one()

        sub = Submission(
            session_id=sess.id,
            user_id=sess.user_id,
            challenge_day_id=assignment.challenge_day_id,
            submission_type="practical" if sess.final_code else "theoretical",
            code=sess.final_code or "",
            note_content=sess.note_content or "",
            score=data.score,
            result=data.result or ("pass" if data.score >= 60 else "fail"),
            docker_output=f"[Admin bahosi]: {data.notes}" if data.notes else None,
        )
        db.add(sub)
        await db.flush()
    else:
        sub.score = data.score
        sub.result = data.result or ("pass" if data.score >= 60 else "fail")
        if data.notes:
            sub.docker_output = (sub.docker_output or "") + f"\n[Admin bahosi]: {data.notes}"

    total_res = await db.execute(
        select(func.sum(Submission.score)).where(Submission.user_id == sub.user_id)
    )
    user_total = total_res.scalar() or 0

    user_res = await db.execute(select(User).where(User.id == sub.user_id))
    user = user_res.scalar_one_or_none()
    if user:
        user.total_score = int(user_total)

    await db.commit()
    await db.refresh(sub)

    return {
        "success": True,
        "id": str(sub.id),
        "score": sub.score,
        "result": sub.result,
        "user_total_score": int(user_total),
        "message": "Yechim muvaffaqiyatli baholandi!",
    }
