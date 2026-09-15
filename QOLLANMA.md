# Python Challenge Platformasi — To'liq Ishga Tushirish va Boshqarish Qo'llanmasi (v2.0)

Ushbu hujjat **Python Challenge Platformasi**ni yangi server yoki kompyuterda noldan boshlab to'liq ishga tushirish, 15 kunlik (225 ta savolli) musobaqani yuklash, anti-cheat monitoringi, yechimlarni ZIP holatida eksport qilish hamda AI agent orqali baholash bo'yicha mukammal amaliy qo'llanmadir.

---

## 📌 Mundarija
1. [Loyiha haqida va Arxitektura](#1-loyiha-haqida-va-arxitektura)
2. [Tizim talablari (Prerequisites)](#2-tizim-talablari-prerequisites)
3. [Konfiguratsiya (.env sozlamalari)](#3-konfiguratsiya-env-sozlamalari)
4. [Docker orqali Ishga Tushirish (1-qadam)](#4-docker-orqali-ishga-tushirish-1-qadam)
5. [Ma'lumotlar Bazasini Tayyorlash (2-qadam)](#5-malumotlar-bazasini-tayyorlash-2-qadam)
6. [Boshlang'ich Ma'lumotlarni Yuklash (3-qadam)](#6-boshlangich-malumotlarni-yuklash-3-qadam)
7. [Foydalanish Jarayoni (Workflow)](#7-foydalanish-jarayoni-workflow)
8. [ZIP Eksport va AI Baholash Tizimi](#8-zip-eksport-va-ai-baholash-tizimi)
9. [Foydali Buyruqlar va Nosozliklarni Bartaraf Etish (Troubleshooting)](#9-foydali-buyruqlar-va-nosozliklarni-bartaraf-etish-troubleshooting)

---

## 1. Loyiha haqida va Arxitektura

Platforma Python o'rganuvchilari va dasturchilar uchun test/musobaqa sinovlarini adolatli va professional tashkil etish uchun ishlab chiqilgan.

### Asosiy texnologiyalar:
- **Backend:** Python 3.11, FastAPI (asinxron REST API), SQLAlchemy 2.0 (asyncpg), Alembic migratsiyalari.
- **Frontend:** React 18, Vite, Monaco Editor (kod muharriri), Zustand (state management), Vanilla CSS (zamonaviy Dark Mode dizayn).
- **Infratuzilma:** Docker, Docker Compose, Nginx (Reverse Proxy), PostgreSQL 16.
- **Xavfsizlik & Anti-Cheat:** Fullscreen nazorati, tabdan chiqish (`visibilitychange`) qaydlari, nusxa olish (Ctrl+V) va DevTools (F12) blokirovkasi, yozish tezligi anomaliyalarini aniqlash.

### Platforma imkoniyatlari (v2.0):
1. **15 Kunlik "Python Asoslari" Musobaqasi:** Jami 225 ta professional savol (har kunga 15 tadan).
2. **Aralash format:**
   - **Amaliy (Practical):** Aniq shart + Monaco Editor + Mantiqiy fikr (Note) maydoni.
   - **Nazariy (Theoretical):** Chuqur tushuncha / arxitektura savoli + Fikr va yechim (Note) maydoni.
3. **Takrorlanmas Random Taqsimlash:** Ishtirokchilar kunga kirganida savollar eng kam berilganlar ichidan tasodifiy tanlanadi. 15 ta turli akkaunt kirsa, ularga 15 xil takrorlanmas savol tushadi.
4. **To'liq Metrikalar:** Sessiyaga kirish, birinchi marta klaviaturada yozishni boshlash, topshirish vaqti, sarflangan aniq soniyalar va avtosaqlanish (`auto_submitted`).
5. **ZIP Eksport:** Barcha ishtirokchilarning to'liq fayllarini bitta bosishda ZIP arxiv qilib yuklab olish.
6. **AI Agent Baholash & Excel Import:** AI agent (ChatGPT, Claude, Gemini) chiqargan ko'p parametrli ballarni Excel orqali yuklash va Leaderboard shakllantirish.

---

## 2. Tizim talablari (Prerequisites)

Loyihani ishga tushirish uchun kompyuter yoki serverda quyidagilar o'rnatilgan bo'lishi kerak:
- **Git** (kodni klonlash uchun)
- **Docker** va **Docker Compose** (Docker Desktop Windows/Mac da yoki Docker Engine Linux da)
- Internet aloqasi (birinchi marta Docker imagelarni yuklash uchun)

---

## 3. Konfiguratsiya (.env sozlamalari)

Loyiha ildiz papkasida `.env.production` fayli mavjud. Server yoki lokal muhitga qarab parametrlarni ko'rib chiqing:

```env
# Ma'lumotlar bazasi
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_secure_pass
POSTGRES_DB=pychallenge
DATABASE_URL=postgresql+asyncpg://postgres:postgres_secure_pass@postgres:5432/pychallenge

# JWT Xavfsizlik
SECRET_KEY=ultra_secret_key_change_in_production_12345
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Muhit
ENVIRONMENT=production
```

---

## 4. Docker orqali Ishga Tushirish (1-qadam)

Loyiha papkasida terminalni oching va barcha konteynerlarni qurib ishga tushiring:

```bash
docker compose up --build -d
```

Bir necha daqiqadan so'ng barcha xizmatlar ishga tushadi:
- `challenge_nginx` — Port 80 (Veb-saytga kirish nuqtasi)
- `challenge_frontend` — React SPA
- `challenge_backend` — FastAPI API (Port 8000 ichki)
- `challenge_postgres` — PostgreSQL bazasi (Port 5434:5432)

Konteynerlar holatini tekshirish:
```bash
docker compose ps
```
Barcha xizmatlar `Up` yoki `Healthy` holatida bo'lishi kerak.

---

## 5. Ma'lumotlar Bazasini Tayyorlash (2-qadam)

Jadvallar va yangi ustunlarni PostgreSQL bazasida avtomatik yaratish uchun Alembic migratsiyasini ishga tushiring:

```bash
docker compose exec backend alembic upgrade head
```

> **Kutilgan natija:** `Running upgrade dfda7c9ed50b -> a1b2c3d4e5f6, v2_question_type_and_ai_scores` xabari chiqadi.

---

## 6. Boshlang'ich Ma'lumotlarni Yuklash (3-qadam)

### 6.1. Bosh Admin akkauntini yaratish:
Platformani boshqarish uchun dastlabki admin akkauntini hosil qiling:
```bash
docker compose exec backend python seed_admin.py
```
- **Login:** `admin@pychallenge.uz`
- **Parol:** `admin123`

### 6.2. 15 Kunlik "Python Asoslari" (225 ta Savol) Challenge ni kiritish:
15 kunlik barcha amaliy va nazariy savollar to'plamini bir zumda bazaga joylashtiring:
```bash
docker compose exec backend python seed_python_basics_challenge.py
```
> **Natija:** 
> - 15 ta kun to'liq yaratiladi;
> - 225 ta savol (119 ta amaliy, 106 ta nazariy) joylashtiriladi;
> - 1-kun darhol ochiq va faol holatga keltiriladi.

---

## 7. Foydalanish Jarayoni (Workflow)

1. **Saytga kirish:**
   Brauzerda quyidagi manzilni oching:
   ```text
   http://localhost
   ```

2. **Admin panel:**
   - Yuqoridagi `admin@pychallenge.uz` / `admin123` ma'lumotlari bilan kiring.
   - [http://localhost/admin](http://localhost/admin) orqali Admin boshqaruv paneliga o'ting.
   - Bu yerda barcha musobaqalar, kunlar va savollarni tahrirlash, o'chirish yoki yangi kun qo'shish mumkin.

3. **Ishtirokchi sifatida qatnashish:**
   - Yangi talaba sifatida ro'yxatdan o'ting (`/register`).
   - "Python Asoslari (15 Kunlik)" musobaqasiga kiring.
   - 1-kunni tanlang:
     - Tizim sizga ushbu kunning 15 ta savolidan bittasini **takrorlanmas tasodifiy** tanlab beradi.
     - Imtihon boshlanadi: Full-screen nazorati, nusxa ko'chirish blokirovkasi, vaqt hisobi.
     - **Amaliy savol bo'lsa:** Monaco Editorda kod yoziladi + Note maydonida mantiqiy yondashuv izohlanadi.
     - **Nazariy savol bo'lsa:** Katta Note maydonida savolga batafsil javob yoziladi.
     - Har 15 soniyada yozilgan harakatlar avtomatik saqlanadi.
     - Vaqt tugasa yoki "Topshirish" tugmasi bosilsa, yechim to'liq metrikalar bilan bazaga topshiriladi.

---

## 8. ZIP Eksport va AI Baholash Tizimi

Musobaqa jarayonida yoki yakunida admin barcha topshiriqlarni tekshirishi uchun maxsus oqim mavjud:

### 8.1. ZIP Arxivni Yuklab Olish:
1. Admin panelga kiring: [http://localhost/admin](http://localhost/admin)
2. Musobaqa kartasidagi **"📦 ZIP"** tugmasini bosing.
3. Barcha ishtirokchilarning topshirgan barcha yechimlari bitta ZIP arxiv fayl sifatida yuklanadi.
4. Arxiv ichida har bir ishtirokchining fayli quyidagi standartda saqlanadi:
   ```text
   PYCHALLENGE SUBMISSION
   ============================================================
   FOYDALANUVCHI: Ali (ali@example.com)
   KUN: Day 1 - 1-kun: Python bilan tanishuv
   SAVOL: Ikki o'zgaruvchi qiymatini almashtirish
   SAVOL TURI: Amaliy (Practical)
   QIYINLIK: easy
   ============================================================
   SAVOL MATNI:
   Ikkita a va b qiymat berilgan...
   ============================================================
   SESSIYAGA KIRISH: 2026-09-15 16:38:12 UTC
   YOZISHNI BOSHLASH: 2026-09-15 16:38:44 UTC
   YUBORISH VAQTI: 2026-09-15 16:41:30 UTC
   SARFLANGAN VAQT: 166 soniya
   QOIDABUZARLIKLAR: 0
   ============================================================
   YECHIM (KOD):
   def swap_values(a, b):
       ...
   ```

### 8.2. AI Agentga Baholatish (Prompt namunasi):
Yuklab olingan fayllarni ChatGPT, Claude yoki Gemini kabi AI agentlarga quyidagi ko'rsatma bilan taqdim etasiz:

> *"Quyidagi talaba yechimlarini tahlil qil va har bir ishtirokchini 5 mezon bo'yicha baholab Excel (.xlsx) jadval qilib ber:*
> *1. Approach (Yondashuv to'g'riligi) — max 25 ball*
> *2. Correctness (Yechim to'g'riligi) — max 35 ball*
> *3. Speed (Sarflangan vaqt tezligi) — max 15 ball*
> *4. Code Quality (Kod sifati / Mantiqiy izoh) — max 15 ball*
> *5. Effort (Harakat / Qoidabuzarlik yo'qligi) — max 10 ball*
> *Ustunlar: email, approach, correctness, speed, quality, effort, notes"*

### 8.3. Excel Natijalarini Tizimga Import Qilish:
1. Admin panelda yuqoridagi **"🤖 AI Baholash"** tugmasini bosing (yoki [http://localhost/admin/scores](http://localhost/admin/scores) ga kiring).
2. Chiqqan Excel (`.xlsx`) faylni Drag & Drop orqali yuklang.
3. Tizim avtomatik ballarni bazaga kiritadi va **AI Leaderboard** reytingini ko'rsatadi.

---

## 9. Foydali Buyruqlar va Nosozliklarni Bartaraf Etish (Troubleshooting)

### Konteynerlar holati va loglarni ko'rish:
```bash
# Barcha konteynerlar holati
docker compose ps

# Backend loglarini jonli ko'rish
docker compose logs -f backend

# Frontend loglarini ko'rish
docker compose logs -f frontend
```

### Konteynerlarni qayta ishga tushirish:
```bash
docker compose restart
```

### Konteynerlarni butunlay to'xtatish:
```bash
docker compose down
```

### Agar port band bo'lsa (Port 80 yoki 5434):
Windows da IIS yoki boshqa xizmat 80-portni band qilgan bo'lsa, `docker-compose.yml` da `nginx` portini `8080:80` qilib o'zgartirishingiz va `http://localhost:8080` orqali kirishingiz mumkin.

---

**Muvaffaqiyatli foydalanish tilaymiz! 🚀**
