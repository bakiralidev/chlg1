import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select  # noqa: E402
from app.db.database import async_session_maker  # noqa: E402
from app.models.models import (  # noqa: E402
    ChallengeResult,
    ConsentLog,
    ExamSession,
    LoginEvent,
    OneTimeCode,
    ParticipantAIScore,
    ScoreAuditLog,
    Submission,
    SupportMessage,
    User,
    UserQuestionAssignment,
    ViolationLog,
)


async def cleanup(confirm: bool) -> int:
    async with async_session_maker() as db:
        res = await db.execute(
            select(User).where(User.is_admin.is_(False)).order_by(User.created_at.asc())
        )
        targets = res.scalars().all()

        if not targets:
            print("O'chiriladigan test (admin bo'lmagan) foydalanuvchilar topilmadi.")
            return 0

        print(f"Admin bo'lmagan foydalanuvchilar ({len(targets)} ta):")
        for u in targets:
            print(f"  - login={u.login} | username={u.username} | status={u.status} | created_at={u.created_at}")

        if not confirm:
            print("\n[DRY-RUN] Hech narsa o'chirilmadi. O'chirish uchun --confirm bayrog'i bilan ishga tushiring.")
            return 0

        answer = input("\nDIQQAT! Yuqoridagi barcha foydalanuvchilar va ularning yozuvlari o'chiriladi. Tasdiqlash uchun 'YES' yozing: ")
        if answer.strip() != "YES":
            print("Bekor qilindi.")
            return 1

        user_ids = [u.id for u in targets]
        sess_subq = select(ExamSession.id).where(ExamSession.user_id.in_(user_ids))

        await db.execute(delete(ScoreAuditLog).where(ScoreAuditLog.user_id.in_(user_ids)))
        await db.execute(delete(ViolationLog).where(ViolationLog.session_id.in_(sess_subq)))
        await db.execute(delete(Submission).where(Submission.user_id.in_(user_ids)))
        await db.execute(delete(ExamSession).where(ExamSession.user_id.in_(user_ids)))
        await db.execute(delete(UserQuestionAssignment).where(UserQuestionAssignment.user_id.in_(user_ids)))
        await db.execute(delete(ChallengeResult).where(ChallengeResult.user_id.in_(user_ids)))
        await db.execute(delete(ParticipantAIScore).where(ParticipantAIScore.user_id.in_(user_ids)))
        await db.execute(delete(OneTimeCode).where(OneTimeCode.user_id.in_(user_ids)))
        await db.execute(delete(SupportMessage).where(SupportMessage.user_id.in_(user_ids)))
        await db.execute(delete(ConsentLog).where(ConsentLog.user_id.in_(user_ids)))
        await db.execute(delete(LoginEvent).where(LoginEvent.user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()

        print(f"Muvaffaqiyatli: {len(user_ids)} ta test foydalanuvchi o'chirildi.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean up non-admin test users safely.")
    parser.add_argument("--confirm", action="store_true", help="Haqiqiy o'chirishga ruxsat berish")
    args = parser.parse_args()
    sys.exit(asyncio.run(cleanup(args.confirm)))


if __name__ == "__main__":
    main()
