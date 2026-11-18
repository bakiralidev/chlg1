from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.models import Challenge, ChallengeResult, User
from app.services.ranking import get_ranking, get_user_rank

router = APIRouter(prefix="/api/v1", tags=["Leaderboard"])


@router.get("/challenges/{challenge_id}/my-rank")
async def get_my_rank(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return ONLY the authenticated user's own rank and score (never other users' scores)."""
    try:
        ch_uuid = uuid.UUID(challenge_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Challenge topilmadi")
    ch_res = await db.execute(select(Challenge).where(Challenge.id == ch_uuid))
    challenge = ch_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    info = await get_user_rank(db, challenge.id, current_user.id)
    if not info:
        return {
            "challenge_id": str(challenge.id),
            "rank": None,
            "total_participants": 0,
            "total_score": current_user.total_score or 0,
            "days_completed": 0,
            "is_tie": False,
        }
    return {"challenge_id": str(challenge.id), **info}


@router.get("/challenges/{challenge_id}/leaderboard")
async def get_leaderboard(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ch_uuid = uuid.UUID(challenge_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Challenge topilmadi")
    ch_res = await db.execute(select(Challenge).where(Challenge.id == ch_uuid))
    challenge = ch_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    if challenge.status != "ended":
        raise HTTPException(
            status_code=403,
            detail="Leaderboard faqat challenge tugagandan keyin ko'rinadi",
        )

    results = await db.execute(
        select(ChallengeResult, User)
        .join(User, ChallengeResult.user_id == User.id)
        .where(ChallengeResult.challenge_id == challenge.id)
        .order_by(ChallengeResult.final_rank.asc())
    )
    rows = results.all()

    return {
        "challenge_id": str(challenge.id),
        "challenge_name": challenge.name,
        "prize_info": challenge.prize_info,
        "leaderboard": [
            {
                "user_id": str(r.User.id),
                "rank": r.ChallengeResult.final_rank,
                "is_tie": bool(r.ChallengeResult.is_tie),
                "username": r.User.username,
                "full_name": r.User.full_name or r.User.username,
                "avatar_url": r.User.avatar_url,
                "total_score": r.ChallengeResult.total_score,
                "days_completed": r.ChallengeResult.days_completed,
                "is_winner": bool(r.ChallengeResult.is_winner),
                "prize_amount": r.ChallengeResult.prize_amount,
            }
            for r in rows
        ],
    }


@router.post("/challenges/{challenge_id}/finalize")
async def finalize_challenge(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Challenge ni tugatish va top natijalarni hisoblash (is_winner final bosqichda belgilanadi)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Faqat adminlar uchun")

    try:
        ch_uuid = uuid.UUID(challenge_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Challenge topilmadi")
    ch_res = await db.execute(select(Challenge).where(Challenge.id == ch_uuid))
    challenge = ch_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    ranking = await get_ranking(db, challenge.id)
    now = datetime.now(timezone.utc)

    existing = await db.execute(
        select(ChallengeResult).where(ChallengeResult.challenge_id == challenge.id)
    )
    for r in existing.scalars().all():
        await db.delete(r)
    await db.flush()

    for entry in ranking:
        cr = ChallengeResult(
            challenge_id=challenge.id,
            user_id=entry["user_id"],
            total_score=entry["total_score"],
            days_completed=entry["days_completed"],
            final_rank=entry["rank"],
            is_tie=entry["is_tie"],
            is_winner=False,
            finalized_at=now,
        )
        db.add(cr)

    challenge.status = "ended"
    await db.commit()

    return {"message": f"Challenge yakunlandi. {len(ranking)} ta ishtirokchi reytinglandi."}
