from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.models.models import Challenge, ChallengeDay, Question, ExamSession, Submission
from app.schemas.admin import (
    ChallengeCreate, ChallengeResponse,
    DayCreate, DayResponse,
    QuestionCreate, QuestionResponse,
    ChallengeStats
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─── CHALLENGES ───────────────────────────────────────────────

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
        raise HTTPException(status_code=400, detail="Tugagan challengeni o'zgartirish mumkin emas")

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

    # Kamida 1 ta kun va savol borligini tekshirish
    days = await db.execute(
        select(func.count()).where(ChallengeDay.challenge_id == challenge_id)
    )
    if days.scalar() == 0:
        raise HTTPException(status_code=400, detail="Challengeda hech qanday kun yo'q")

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
                select(ChallengeDay.id).where(ChallengeDay.challenge_id == challenge_id)
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


# ─── DAYS ─────────────────────────────────────────────────────

@router.post("/days", response_model=DayResponse, status_code=201)
async def create_day(
    data: DayCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    # Challenge mavjudligini tekshirish
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


# ─── QUESTIONS ────────────────────────────────────────────────

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
    payload["test_cases"] = [tc for tc in payload["test_cases"]]  # JSONB uchun

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
    return {"message": "Savol o'chirildi"}


# ─── Helpers ──────────────────────────────────────────────────

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
        "title": q.title, "difficulty": q.difficulty, "created_at": q.created_at,
    }
