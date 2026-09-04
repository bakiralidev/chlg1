import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import async_session_maker
from app.models.models import User
from app.core.security import hash_password

async def seed_admin():
    async with async_session_maker() as session:
        result = await session.execute(select(User).filter_by(email="admin@pychallenge.uz"))
        admin = result.scalar_one_or_none()

        if not admin:
            print("Yangi admin yaratilmoqda...")
            admin_user = User(
                email="admin@pychallenge.uz",
                password_hash=hash_password("admin123"),  # kuchli parolga almashtiring
                username="Admin",
                is_admin=True,
                level=999
            )
            session.add(admin_user)
            await session.commit()
            print("Admin muvaffaqiyatli yaratildi! Email: admin@pychallenge.uz | Parol: admin123")
        else:
            print("Admin allaqachon mavjud!")

if __name__ == "__main__":
    asyncio.run(seed_admin())
