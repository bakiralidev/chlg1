"""
Background Tasks — Avto-submit cron va Challenge tugash croni
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.models.models import (
    ExamSession, UserQuestionAssignment, ChallengeDay,
    Challenge, Submission, User, ChallengeResult, Question
)
from app.services.sandbox_service import run_code_in_sandbox

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


# ─── Helper: session uchun async session factory ─────────────────────────────

async def _get_session() -> AsyncSession:
    return async_session_maker()


# ─── Avto-Submit Cron (har 1 daqiqada) ───────────────────────────────────────

async def auto_submit_expired_sessions():
    """
    Vaqti tugagan (expires_at < now) va hali 'active' bo'lgan
    sessiyalarni topib, final_code mavjud bo'lsa yuboradi.
    """
    logger.info("[CRON] Avto-submit tekshiruvi boshlandi")
    now = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        try:
            # Muddati tugagan faol sessiyalarni topish
            result = await db.execute(
                select(ExamSession).where(
                    and_(
                        ExamSession.status == "active",
                        ExamSession.expires_at < now
                    )
                )
            )
            expired_sessions = result.scalars().all()

            if not expired_sessions:
                logger.info("[CRON] Avto-submit: tugagan sessiya yo'q")
                return

            logger.info(f"[CRON] {len(expired_sessions)} ta tugagan sessiya topildi")

            for session in expired_sessions:
                try:
                    await _process_expired_session(session, db, now)
                except Exception as e:
                    logger.error(f"[CRON] Sessiya {session.id} xatosi: {e}")

            await db.commit()
            logger.info("[CRON] Avto-submit yakunlandi")

        except Exception as e:
            await db.rollback()
            logger.error(f"[CRON] Avto-submit umumiy xato: {e}")


async def _process_expired_session(session: ExamSession, db: AsyncSession, now: datetime):
    """Bitta muddati tugagan sessiyani qayta ishlash"""
    if session.final_code:
        # Savolni olish
        assign_res = await db.execute(
            select(UserQuestionAssignment).where(
                UserQuestionAssignment.id == session.assignment_id
            )
        )
        assignment = assign_res.scalar_one_or_none()
        if not assignment:
            session.status = "expired"
            return

        question_res = await db.execute(
            select(Question).where(Question.id == assignment.question_id)
        )
        question = question_res.scalar_one_or_none()
        if not question:
            session.status = "expired"
            return

        # Docker sandbox da baholash
        result = await run_code_in_sandbox(session.final_code, question.test_cases)
        passed = result.get("passed", 0)
        total = result.get("total", 1)
        score = round((passed / total) * 10) if total > 0 else 0

        # Submission yozish
        submission = Submission(
            session_id=session.id,
            user_id=session.user_id,
            challenge_day_id=assignment.challenge_day_id,
            code=session.final_code,
            result=result.get("status", "error"),
            score=score,
            execution_ms=result.get("execution_ms"),
            docker_output=result.get("output"),
        )
        db.add(submission)

        # Foydalanuvchi balini yangilash
        user_res = await db.execute(select(User).where(User.id == session.user_id))
        user = user_res.scalar_one_or_none()
        if user:
            user.total_score += score

        session.status = "auto_submitted"
        session.submitted_at = now
        session.is_readonly = True

        logger.info(
            f"[CRON] Sessiya {session.id} avto-yuborildi: {score}/10 ball"
        )
    else:
        # Kod yo'q — shunchaki muddati tugdi
        session.status = "expired"
        session.is_readonly = True
        logger.info(f"[CRON] Sessiya {session.id} muddati tugadi (kod yo'q)")


# ─── Challenge Tugash Croni (har 5 daqiqada) ─────────────────────────────────

async def finalize_ended_challenges():
    """
    end_date o'tgan va hali 'active' holatdagi challengelarni
    'ended' ga o'tkazib, challenge_results ni hisoblaydi.
    """
    logger.info("[CRON] Challenge tugash tekshiruvi boshlandi")
    now = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        try:
            # Tugash sanasi o'tgan faol challengelar
            ch_result = await db.execute(
                select(Challenge).where(Challenge.status == "active")
            )
            challenges = ch_result.scalars().all()

            for challenge in challenges:
                from datetime import timedelta
                end_date = challenge.start_date + timedelta(days=challenge.total_days)
                if end_date > now:
                    continue  # Hali tugamagan

                logger.info(f"[CRON] Challenge '{challenge.name}' tugadi, natijalar hisoblanmoqda")
                await _finalize_challenge(challenge, db, now)

            await db.commit()
            logger.info("[CRON] Challenge tugash tekshiruvi yakunlandi")

        except Exception as e:
            await db.rollback()
            logger.error(f"[CRON] Challenge tugash xatosi: {e}")


async def _finalize_challenge(challenge: Challenge, db: AsyncSession, now: datetime):
    """Challenge natijalarini hisoblash va g'olibni aniqlash"""
    # Barcha submissionlarni olish
    sub_result = await db.execute(
        select(
            Submission.user_id,
            Submission.score,
            Submission.challenge_day_id
        ).where(
            Submission.challenge_day_id.in_(
                select(ChallengeDay.id).where(
                    ChallengeDay.challenge_id == challenge.id
                )
            )
        )
    )
    submissions = sub_result.all()

    # Foydalanuvchi bo'yicha guruhlash
    user_stats: dict = {}
    for user_id, score, day_id in submissions:
        uid = str(user_id)
        if uid not in user_stats:
            user_stats[uid] = {"total_score": 0, "days": set()}
        user_stats[uid]["total_score"] += (score or 0)
        user_stats[uid]["days"].add(str(day_id))

    # Ranklar bo'yicha saralash
    ranked = sorted(
        user_stats.items(),
        key=lambda x: (-x[1]["total_score"], -len(x[1]["days"]))
    )

    for rank, (user_id_str, stats) in enumerate(ranked, start=1):
        import uuid
        user_id = uuid.UUID(user_id_str)

        # Mavjud natijani tekshirish
        existing = await db.execute(
            select(ChallengeResult).where(
                ChallengeResult.challenge_id == challenge.id,
                ChallengeResult.user_id == user_id
            )
        )
        cr = existing.scalar_one_or_none()

        if cr:
            cr.total_score = stats["total_score"]
            cr.days_completed = len(stats["days"])
            cr.final_rank = rank
            cr.is_winner = (rank == 1)
            cr.finalized_at = now
        else:
            cr = ChallengeResult(
                challenge_id=challenge.id,
                user_id=user_id,
                total_score=stats["total_score"],
                days_completed=len(stats["days"]),
                final_rank=rank,
                is_winner=(rank == 1),
                finalized_at=now,
            )
            db.add(cr)

    # Challengeni 'ended' ga o'tkazish
    challenge.status = "ended"
    logger.info(
        f"[CRON] Challenge '{challenge.name}' yakunlandi. "
        f"{len(ranked)} ta ishtirokchi, g'olib rank-1"
    )


# ─── Scheduler boshqaruvi ────────────────────────────────────────────────────

def start_scheduler():
    """Schedulerni ishga tushirish (startup eventda chaqiriladi)"""
    # Har 1 daqiqada avto-submit
    scheduler.add_job(
        auto_submit_expired_sessions,
        trigger="interval",
        minutes=1,
        id="auto_submit",
        replace_existing=True,
        max_instances=1,
    )
    # Har 5 daqiqada challenge tugash tekshiruvi
    scheduler.add_job(
        finalize_ended_challenges,
        trigger="interval",
        minutes=5,
        id="finalize_challenges",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("[SCHEDULER] Ishga tushdi: auto_submit (1min), finalize_challenges (5min)")


def stop_scheduler():
    """Schedulerni to'xtatish (shutdown eventda chaqiriladi)"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] To'xtatildi")
