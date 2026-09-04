from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.models.models import (
    Challenge, ChallengeDay, ChallengeResult,
    User, Submission, ExamSession, UserQuestionAssignment
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Leaderboard"])


@router.get("/challenges/{challenge_id}/leaderboard")
async def get_leaderboard(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ch_res = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = ch_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    # Leaderboard faqat tugagandan keyin ochiladi
    if challenge.status != "ended":
        raise HTTPException(
            status_code=403,
            detail="Leaderboard faqat challenge tugagandan keyin ko'rinadi"
        )

    # challenge_results dan tortib chiqarish
    results = await db.execute(
        select(ChallengeResult, User)
        .join(User, ChallengeResult.user_id == User.id)
        .where(ChallengeResult.challenge_id == challenge_id)
        .order_by(ChallengeResult.final_rank)
    )
    rows = results.all()

    return {
        "challenge_id": challenge_id,
        "challenge_name": challenge.name,
        "prize_info": challenge.prize_info,
        "leaderboard": [
            {
                "rank": r.ChallengeResult.final_rank,
                "username": r.User.username,
                "avatar_url": r.User.avatar_url,
                "total_score": r.ChallengeResult.total_score,
                "days_completed": r.ChallengeResult.days_completed,
                "is_winner": r.ChallengeResult.is_winner,
            }
            for r in rows
        ]
    }


@router.post("/challenges/{challenge_id}/finalize")
async def finalize_challenge(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Challenge ni tugating va leaderboardni hisoblang (faqat admin yoki cron chaqiradi)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Faqat adminlar uchun")

    ch_res = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = ch_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge topilmadi")

    # Har bir foydalanuvchining umumiy ballini hisoblash
    score_query = await db.execute(
        select(
            Submission.user_id,
            func.sum(Submission.score).label("total"),
            func.count(Submission.id.distinct()).label("days"),
        )
        .where(
            Submission.challenge_day_id.in_(
                select(ChallengeDay.id).where(ChallengeDay.challenge_id == challenge_id)
            )
        )
        .group_by(Submission.user_id)
        .order_by(func.sum(Submission.score).desc())
    )
    rows = score_query.all()

    # Mavjud natijalarni tozalash
    existing = await db.execute(
        select(ChallengeResult).where(ChallengeResult.challenge_id == challenge_id)
    )
    for r in existing.scalars().all():
        await db.delete(r)

    # Yangi natijalar yozish
    for rank, row in enumerate(rows, start=1):
        cr = ChallengeResult(
            challenge_id=challenge_id,
            user_id=row.user_id,
            total_score=row.total or 0,
            days_completed=row.days or 0,
            final_rank=rank,
            is_winner=(rank == 1),
            finalized_at=func.now()
        )
        db.add(cr)

    challenge.status = "ended"
    await db.commit()

    return {"message": f"Challenge yakunlandi. {len(rows)} ta ishtirokchi reytinglandi."}
