# PyChallenge Telegram Bot

Telegram bot orqali ishtirokchilarni ro'yxatdan o'tkazish, bir martalik parol (OTP) berish, parolni tiklash, qatnashishni tasdiqlash ("Tayyorman"), kutish ro'yxati (waitlist) va admin boshqaruvi amalga oshiriladi.

## 1. Muhit o'zgaruvchilari (`.env`)

Loyiha ildizidagi `.env` faylida (namuna: `.env.example`) quyidagi o'zgaruvchilar bo'lishi kerak:

- `TELEGRAM_BOT_TOKEN` — @BotFather dan olingan token
- `TELEGRAM_BOT_USERNAME` — bot username (masalan `pychallenge_uz_bot`)
- `ADMIN_TELEGRAM_IDS` — adminlarning Telegram ID lari (vergul bilan ajratilgan)
- `MAX_PARTICIPANTS=30` — asosiy o'rinlar soni
- `CHALLENGE_START_DATE=2027-02-01`
- `REGISTRATION_CLOSE_DATE=2027-01-25`
- `CONFIRM_WINDOW_START=2027-01-28`
- `CONFIRM_WINDOW_END=2027-01-31`
- `FINAL_DATE=2027-03-05`
- `RULES_VERSION=1`
- `SITE_URL` — sayt manzili
- `OTP_TTL_MINUTES=15`
- `OTP_MAX_PER_HOUR=3`
- `TIMEZONE=Asia/Tashkent`

## 2. Migratsiya

Bot yangi jadvallar yaratmaydi, barcha schema o'zgarishlari `backend` Alembic migratsiyalari orqali bajariladi:

```bash
cd backend
alembic upgrade head
```

Orqaga qaytarish (tekshirish uchun):

```bash
alembic downgrade -1
```

## 3. Docker bilan ishga tushirish

```bash
docker compose up -d --build
```

Bot loglarini ko'rish:

```bash
docker compose logs -f bot
```

Bot alohida konteynerda (`challenge_bot`) ishlaydi — bot to'xtasa ham sayt ishlashda davom etadi.

## 4. Lokal ishga tushirish (dev)

```bash
# Loyiha ildizidan
PYTHONPATH=.:backend python -m bot.main
```

## 5. Admin buyruqlari

Faqat `ADMIN_TELEGRAM_IDS` ro'yxatidagi foydalanuvchilar uchun:

- `/stats` — foydalanuvchilar statistikasi
- `/broadcast <matn>` yoki `/broadcast <status> <matn>` — ommaviy xabar
- `/ban <telegram_id|login> <sabab>` / `/unban <telegram_id|login>`
- `/disqualify <login> <sabab>`
- `/user <login|telegram_id>` — foydalanuvchi ma'lumotlari
- `/export` — `.xlsx` eksport
- `/reply <telegram_id> <matn>` — support xabariga javob (yoki xabarga reply qilish)
