"""
Background Tasks — Avto-submit cron, Challenge tugash croni, LoginAttempt tozalash
"""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import async_session_maker
from app.models.models import (
    Challenge,
    ChallengeResult,
    ExamSession,
    LoginAttempt,
    Question,
    Submission,
    UserQuestionAssignment,
)
from app.services.ranking import get_ranking
from app.services.scoring import evaluate_practical, recalculate_total

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)


async def auto_submit_expired_sessions():
    """
    Vaqti tugagan (expires_at < now) va hali 'active' bo'lgan
    sessiyalarni topib, avto-baholash bilan yuboradi.
    """
    logger.info("[CRON] Avto-submit tekshiruvi boshlandi")
    now = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(ExamSession).where(
                    and_(
                        ExamSession.status == "active",
                        ExamSession.expires_at < now,
                    )
                )
            )
            expired_sessions = result.scalars().all()

            if not expired_sessions:
                return

            logger.info("[CRON] %s ta tugagan sessiya topildi", len(expired_sessions))
            for session in expired_sessions:
                try:
                    await _process_expired_session(session, db, now)
                except Exception as e:
                    logger.error("[CRON] Sessiya %s xatosi: %s", session.id, e)

            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("[CRON] Avto-submit umumiy xato: %s", e)


async def _process_expired_session(session: ExamSession, db: AsyncSession, now: datetime):
    assign_res = await db.execute(
        select(UserQuestionAssignment).where(
            UserQuestionAssignment.id == session.assignment_id
        )
    )
    assignment = assign_res.scalar_one_or_none()
    if not assignment:
        session.status = "expired"
        session.is_readonly = True
        return

    question_res = await db.execute(
        select(Question).where(Question.id == assignment.question_id)
    )
    question = question_res.scalar_one_or_none()
    if not question:
        session.status = "expired"
        session.is_readonly = True
        return

    has_answer = bool(session.final_code or session.note_content)
    if not has_answer:
        session.status = "expired"
        session.is_readonly = True
        return

    score = 0
    result_status = "manual_review"
    execution_ms = None
    docker_output = None

    if question.question_type == "practical" and session.final_code:
        eval_res = await evaluate_practical(session.final_code, question)
        score = eval_res["score"]
        result_status = eval_res["result"]
        execution_ms = eval_res["execution_ms"]
        docker_output = eval_res["output"]

    submission = Submission(
        session_id=session.id,
        user_id=session.user_id,
        challenge_day_id=assignment.challenge_day_id,
        submission_type=question.question_type,
        code=session.final_code,
        note_content=session.note_content,
        result=result_status,
        score=score,
        execution_ms=execution_ms,
        docker_output=docker_output,
        submitted_at=now,
    )
    db.add(submission)
    await db.flush()

    await recalculate_total(db, session.user_id)

    session.status = "auto_submitted"
    session.submitted_at = now
    session.is_readonly = True


async def finalize_ended_challenges():
    """
    end_date o'tgan va hali 'active' holatdagi challengelarni
    'ended' ga o'tkazib, challenge_results ni hisoblaydi (is_winner=False, finalgacha).
    """
    now_local = settings.now_local()

    async with async_session_maker() as db:
        try:
            ch_result = await db.execute(
                select(Challenge).where(Challenge.status == "active")
            )
            challenges = ch_result.scalars().all()

            for challenge in challenges:
                start_local = (
                    challenge.start_date.astimezone(settings.tz)
                    if challenge.start_date.tzinfo
                    else challenge.start_date.replace(tzinfo=settings.tz)
                )
                end_date = start_local + timedelta(days=challenge.total_days)
                if end_date > now_local:
                    continue

                await _finalize_challenge(challenge, db, datetime.now(timezone.utc))

            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("[CRON] Challenge tugash xatosi: %s", e)


async def _finalize_challenge(challenge: Challenge, db: AsyncSession, now: datetime):
    ranking = await get_ranking(db, challenge.id)

    for entry in ranking:
        existing = await db.execute(
            select(ChallengeResult).where(
                ChallengeResult.challenge_id == challenge.id,
                ChallengeResult.user_id == entry["user_id"],
            )
        )
        cr = existing.scalar_one_or_none()
        if cr:
            cr.total_score = entry["total_score"]
            cr.days_completed = entry["days_completed"]
            cr.final_rank = entry["rank"]
            cr.is_tie = entry["is_tie"]
            cr.finalized_at = now
        else:
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


async def cleanup_old_login_attempts():
    """7 kundan eski login_attempts yozuvlarini tozalash."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    async with async_session_maker() as db:
        try:
            await db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("[CRON] LoginAttempt tozalash xatosi: %s", e)


def start_scheduler():
    scheduler.add_job(
        auto_submit_expired_sessions,
        trigger="interval",
        minutes=1,
        id="auto_submit",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        finalize_ended_challenges,
        trigger="interval",
        minutes=5,
        id="finalize_challenges",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        cleanup_old_login_attempts,
        trigger="cron",
        hour=3,
        minute=15,
        id="cleanup_login_attempts",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("[SCHEDULER] Ishga tushdi (%s)", settings.TIMEZONE)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] To'xtatildi")
