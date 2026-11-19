# PyChallenge — Ishga Tushirish, Restart va Boshqarish Qo'llanmasi

Ushbu qo'llanma loyihaning barcha 6 ta xizmati (`postgres`, `runner`, `backend`, `bot`, `frontend`, `nginx`) ni ishga tushirish, qayta ishga tushirish (restart), migratsiya qilish, tekshirish va Git'ga yuklash uchun amaliy ko'rsatmalarni o'z ichiga oladi.

---

## 1. Muhit o'zgaruvchilari (`.env`)

Loyiha ildizida bitta umumiy `.env` fayl ishlatiladi (`.env` Git'ga yuklanmaydi). Namuna: `.env.example`.

Yangi serverda boshlashdan oldin `.env.example` dan `.env` yarating va quyidagi muhim qiymatlarni to'ldiring:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`
- `JWT_SECRET` (kamida 32 belgili tasodifiy satr)
- `RUNNER_SHARED_SECRET` (kamida 32 belgili tasodifiy satr)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `ADMIN_TELEGRAM_IDS`
- `SITE_URL`, `ALLOWED_ORIGINS`
- Challenge sanalari: `CHALLENGE_START_DATE`, `REGISTRATION_CLOSE_DATE`, `CONFIRM_WINDOW_START`, `CONFIRM_WINDOW_END`, `FINAL_DATE`, `TIMEZONE=Asia/Tashkent`

---

## 2. Birinchi marta ishga tushirish

```bash
# 1. Barcha konteynerlarni qurish va ishga tushirish
docker compose up -d --build

# 2. Holatni tekshirish (barchasi Up / Healthy bo'lishi kerak)
docker compose ps

# 3. Baza migratsiyasini bajarish
docker compose exec backend alembic upgrade head

# 4. (Ixtiyoriy) Boshlang'ich admin yaratish
docker compose exec backend python seed_admin.py
```

---

## 3. Restart berish (Qayta ishga tushirish)

### Oddiy restart (kod yoki konfiguratsiya o'zgarmagan bo'lsa):
```bash
# Barcha xizmatlarni restart qilish
docker compose restart

# Yoki faqat bitta xizmatni restart qilish
docker compose restart backend
docker compose restart bot
docker compose restart runner
docker compose restart nginx
```

### `.env` fayl o'zgartirilganda:
`restart` buyrug'i `.env` ni qayta o'qimaydi! Konteynerni qayta yaratish kerak:
```bash
docker compose up -d --force-recreate
```

### Kod (`backend/`, `bot/`, `runner/`, `frontend/`) o'zgartirilganda:
```bash
# Hammasini qayta qurish va ishga tushirish
docker compose up -d --build

# Yoki faqat o'zgargan xizmatni
docker compose up -d --build backend
docker compose up -d --build runner
docker compose up -d --build bot
```

### To'xtatish:
```bash
docker compose down
```
*(Eslatma: `docker compose down -v` ishlatmang, aks holda PostgreSQL bazasidagi barcha ma'lumotlar o'chib ketadi!)*

---

## 4. Loglarni ko'rish

```bash
docker compose logs -f backend
docker compose logs -f bot
docker compose logs -f runner
docker compose logs --tail=100 postgres
```

---

## 5. Baza migratsiyalari (Alembic)

```bash
# Oxirgi versiyaga yangilash
docker compose exec backend alembic upgrade head

# Joriy versiyani ko'rish
docker compose exec backend alembic current

# 1 qadam orqaga qaytarish (tekshirish uchun)
docker compose exec backend alembic downgrade -1
```

---

## 6. Savollarni yuklash va tekshirish

JSON formati namunasi: `scripts/sample_questions.json` (batafsil: `docs/questions-format.md`).

```bash
# 1. Bazaga yozmasdan formatni tekshirish (dry-run)
python scripts/import_questions.py scripts/sample_questions.json --challenge-id <CHALLENGE_UUID> --dry-run

# 2. Bazaga yuklash
python scripts/import_questions.py scripts/sample_questions.json --challenge-id <CHALLENGE_UUID>

# 3. Amaliy savollarning reference_solution kodini runner'da tekshirish
docker compose cp scripts/validate_questions.py backend:/tmp/validate_questions.py
docker compose exec backend python /tmp/validate_questions.py --challenge-id <CHALLENGE_UUID>
```

---

## 7. Test va Zaxira (Backup)

### Test foydalanuvchilarni tozalash (challenge boshlanishidan oldin):
```bash
# Avval ro'yxatni ko'rish (o'chirmaydi)
docker compose exec backend python /app/../scripts/cleanup_test_users.py
# Yoki lokal Python'dan:
python scripts/cleanup_test_users.py

# Haqiqiy o'chirish (tasdiqlash uchun YES yoziladi)
python scripts/cleanup_test_users.py --confirm
```

### PostgreSQL zaxira nusxa (Backup / Restore):
```bash
# Zaxira olish (./backups/ papkasiga oxirgi 14 tasini saqlaydi)
./scripts/backup.sh
```
Tiklash bo'yicha yo'riqnoma: `docs/backup.md`. HTTPS (Let's Encrypt) sozlash: `docs/https.md`.

---

## 8. Sinovlar (Tests)

```bash
# 1. Backend & Runner unit-testlari (lokal)
python -m pytest -p no:locust -p no:asyncio -p no:anyio backend/tests -v

# 2. Runner jonli hujum sinovi (16 ta test, Docker ishlayotganda)
docker compose cp scripts/sandbox_attack_test.py backend:/tmp/sandbox_attack_test.py
docker compose exec backend python /tmp/sandbox_attack_test.py
```

---

## 9. Git'ga yuklash

```bash
# Holatni tekshirish (.env va vaqtinchalik fayllar kirmasligiga ishonch hosil qiling)
git status

# Hozirgi branch'ni push qilish
git push -u origin fix/runner-isolation

# Agar main branch'ga birlashtirmoqchi bo'lsangiz:
git checkout main
git merge fix/runner-isolation
git push origin main
```
