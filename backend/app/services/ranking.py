from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ChallengeDay,
    ExamSession,
    Submission,
    User,
    UserQuestionAssignment,
    ViolationLog,
)


async def get_ranking(db: AsyncSession, challenge_id: Any) -> list[dict[str, Any]]:
    """
    Compute challenge ranking using the official tie-breaker rules:
      1) higher total_score
      2) more days_completed
      3) fewer total_violations
      4) less total_time_spent_secs
    Entries with all 4 keys equal share the same rank and have is_tie=True.
    Only non-admin confirmed users are ranked.
    """
    day_ids_subq = select(ChallengeDay.id).where(ChallengeDay.challenge_id == challenge_id)

    users_res = await db.execute(
        select(User).where(User.is_admin.is_(False), User.status == "confirmed")
    )
    participants = users_res.scalars().all()
    if not participants:
        return []

    # 1. Submissions aggregation per user for this challenge
    sub_res = await db.execute(
        select(
            Submission.user_id,
            func.coalesce(func.sum(Submission.score), 0).label("total_score"),
            func.count(func.distinct(Submission.challenge_day_id)).label("days_completed"),
        )
        .where(Submission.challenge_day_id.in_(day_ids_subq))
        .group_by(Submission.user_id)
    )
    sub_map = {
        str(r.user_id): (int(r.total_score or 0), int(r.days_completed or 0))
        for r in sub_res.all()
    }

    # 2. Violations count per user for this challenge
    viol_res = await db.execute(
        select(
            ExamSession.user_id,
            func.count(ViolationLog.id).label("violations"),
        )
        .join(ExamSession, ViolationLog.session_id == ExamSession.id)
        .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
        .where(UserQuestionAssignment.challenge_day_id.in_(day_ids_subq))
        .group_by(ExamSession.user_id)
    )
    viol_map = {str(r.user_id): int(r.violations or 0) for r in viol_res.all()}

    # 3. Total time spent in submitted/auto_submitted sessions for this challenge
    time_res = await db.execute(
        select(
            ExamSession.user_id,
            func.coalesce(func.sum(ExamSession.time_spent_secs), 0).label("time_spent"),
        )
        .join(UserQuestionAssignment, ExamSession.assignment_id == UserQuestionAssignment.id)
        .where(
            UserQuestionAssignment.challenge_day_id.in_(day_ids_subq),
            ExamSession.status.in_(["submitted", "auto_submitted"]),
        )
        .group_by(ExamSession.user_id)
    )
    time_map = {str(r.user_id): int(r.time_spent or 0) for r in time_res.all()}

    entries: list[dict[str, Any]] = []
    for u in participants:
        uid = str(u.id)
        total_score, days_completed = sub_map.get(uid, (0, 0))
        total_violations = viol_map.get(uid, 0)
        total_time_spent = time_map.get(uid, 0)
        sort_key = (-total_score, -days_completed, total_violations, total_time_spent)
        entries.append(
            {
                "user_id": u.id,
                "user_id_str": uid,
                "login": u.login,
                "username": u.username,
                "full_name": u.full_name or u.username,
                "avatar_url": u.avatar_url,
                "total_score": total_score,
                "days_completed": days_completed,
                "total_violations": total_violations,
                "total_time_spent_secs": total_time_spent,
                "_sort_key": sort_key,
            }
        )

    entries.sort(key=lambda e: (e["_sort_key"], e["user_id_str"]))

    # Assign ranks and detect ties
    key_counts: dict[tuple, int] = {}
    for e in entries:
        key_counts[e["_sort_key"]] = key_counts.get(e["_sort_key"], 0) + 1

    prev_key = None
    current_rank = 0
    for idx, e in enumerate(entries, start=1):
        sk = e["_sort_key"]
        if sk != prev_key:
            current_rank = idx
            prev_key = sk
        e["rank"] = current_rank
        e["is_tie"] = key_counts[sk] > 1
        e.pop("_sort_key", None)

    return entries


async def get_user_rank(db: AsyncSession, challenge_id: Any, user_id: Any) -> Optional[dict[str, Any]]:
    ranking = await get_ranking(db, challenge_id)
    uid = str(user_id)
    total_participants = len(ranking)
    for entry in ranking:
        if entry["user_id_str"] == uid:
            return {
                "rank": entry["rank"],
                "total_participants": total_participants,
                "total_score": entry["total_score"],
                "days_completed": entry["days_completed"],
                "total_violations": entry["total_violations"],
                "total_time_spent_secs": entry["total_time_spent_secs"],
                "is_tie": entry["is_tie"],
            }
    return None
