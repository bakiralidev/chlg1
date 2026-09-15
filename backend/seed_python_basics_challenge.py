"""
Python Asoslari (15 Kunlik) Challenge va 225 ta savolni bazaga kiritish skripti.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete

from app.db.database import async_session_maker
from app.models.models import Challenge, ChallengeDay, Question, User
from challenge_data import ALL_15_DAYS


async def seed_challenge():
    async with async_session_maker() as session:
        print("=== Python Asoslari Challenge Seeding boshlandi ===")

        # 1. Admin foydalanuvchini olish
        res = await session.execute(select(User).filter_by(email="admin@pychallenge.uz"))
        admin = res.scalar_one_or_none()
        if not admin:
            res_any = await session.execute(select(User).filter_by(is_admin=True))
            admin = res_any.scalar_one_or_none()

        admin_id = admin.id if admin else None

        # 2. Eskisini tekshirish
        challenge_name = "Python Asoslari (15 Kunlik)"
        existing_res = await session.execute(
            select(Challenge).filter_by(name=challenge_name)
        )
        existing_ch = existing_res.scalar_one_or_none()

        if existing_ch:
            print(f"Eski '{challenge_name}' challenge topildi, o'chirib yangidan kiritilmoqda...")
            await session.delete(existing_ch)
            await session.commit()

        # 3. Yangi Challenge yaratish
        now = datetime.now(timezone.utc)
        challenge = Challenge(
            name=challenge_name,
            description=(
                "Python dasturlash tili asoslari bo'yicha 15 kunlik intensiv musobaqa. "
                "Har bir kun uchun 15 tadan amaliy va nazariy savollar to'plami."
            ),
            total_days=15,
            # Start date 1 soat oldinga qo'yiladi, shunda 1-kun darhol ochiq va faol bo'ladi
            start_date=now - timedelta(hours=1),
            prize_info="G'oliblar uchun qimmatbaho sovg'alar va sertifikatlar",
            status="active",
            max_violations=3,
            created_by=admin_id,
        )
        session.add(challenge)
        await session.flush()
        print(f"Yangi Challenge yaratildi: ID={challenge.id}, Nomi='{challenge.name}', Status={challenge.status}")

        total_questions_count = 0
        practical_count = 0
        theoretical_count = 0

        # 4. Kunlar va savollarni yaratish
        for day_info in ALL_15_DAYS:
            day = ChallengeDay(
                challenge_id=challenge.id,
                day_number=day_info["day_number"],
                title=day_info["title"],
                time_limit_secs=day_info["time_limit_secs"],
            )
            session.add(day)
            await session.flush()

            for q in day_info["questions"]:
                question = Question(
                    challenge_day_id=day.id,
                    title=q["title"],
                    question_type=q["question_type"],
                    difficulty=q["difficulty"],
                    body_text=q["body_text"],
                    starter_code=q.get("starter_code", ""),
                )
                session.add(question)
                total_questions_count += 1
                if q["question_type"] == "practical":
                    practical_count += 1
                else:
                    theoretical_count += 1

            mins = day_info["time_limit_secs"] // 60
            print(f"  [+] {day_info['title']} - {len(day_info['questions'])} ta savol qo'shildi (Vaqt: {mins} daqiqa)")

        await session.commit()

        print("\n=== Muvaffaqiyatli yakunlandi! ===")
        print(f"Jami kunlar: 15 ta")
        print(f"Jami savollar: {total_questions_count} ta")
        print(f"  - Amaliy (practical): {practical_count} ta")
        print(f"  - Nazariy (theoretical): {theoretical_count} ta")
        print(f"Challenge ID: {challenge.id}")


if __name__ == "__main__":
    asyncio.run(seed_challenge())
