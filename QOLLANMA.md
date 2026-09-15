# Python Challenge Platformasi — Loyiha Tahlili va Ishga Tushirish Qo'llanmasi

Ushbu hujjat loyihaning to'liq tahlili, yangilangan imkoniyatlari (Nazariy/Amaliy savollar, ZIP eksport, AI orqali baholash) hamda tizimni lokal va server (production) muhitida ishga tushirish bo'yicha batafsil qo'llanmani o'z ichiga oladi.

---

## 1. Loyiha Arxitekturasi va Yangi Imkoniyatlar (Architecture & Features)

Loyiha Python dasturchilari va o'quvchilari uchun test/imtihon va 30 kunlik challenge musobaqalarini o'tkazishga mo'ljallangan to'liq tizimdir.

### 1.1 Backend (Python 3.11 / FastAPI)
*   **Freymvork:** FastAPI (asinxron, yuqori tezlikdagi RESTful API).
*   **Ma'lumotlar bazasi:** PostgreSQL 16 (SQLAlchemy 2.0 asinxron ORM va Alembic migratsiyalari bilan).
*   **Xavfsizlik & Auth:** JWT Access Token, parollarni bcrypt heshlash, rollar tizimi (Admin / Ishtirokchi).
*   **Fonda ishlovchi vazifalar (Background Tasks):**
    *   Vaqti tugagan sessiyalarni avtomatik tarzda topshirish (`auto_submitted`).
    *   Musobaqa yakunlanganda natijalarni hisoblash.

### 1.2 Frontend (React 18 / Vite)
*   **Muharrir:** Monaco Editor (VS Code texnologiyasi) — sintaksisni yoritish va avtomatik qatorlar.
*   **Anti-Cheat monitoringi:**
    *   Full-Screen rejimi nazorati.
    *   Tab yoki oynadan chiqish holatlari (`visibilitychange`) qayd etiladi.
    *   Ctrl+V (nusxa ko'chirish) va DevTools (F12) bloklanadi.
    *   Haddan tashqari g'ayritabiiy yozish tezligi aniqlanadi.
    *   Maksimal qoidabuzarliklar sonidan oshsa, ishtirokchi diskvalifikatsiya qilinadi.

---

## 2. Yangi Qo'shilgan Maxsus Imkoniyatlar

### 2.1 Yangilangan Savol Qo'shish Formati (Nazariy va Amaliy)
Savol yaratish jarayoni soddalashtirildi va 2 xil toifaga ajratildi:
1.  **Amaliy (Practical):**
    *   Savol matni va boshlang'ich kod (starter code).
    *   Ishtirokchi uchun: **Monaco Editor** (kod yozish oynasi) + **Note (Mantiqiy yondashuv / Fikr)** maydoni.
2.  **Nazariy (Theoretical):**
    *   Savol matni.
    *   Ishtirokchi uchun: Fikr, mantiq va javobni erkin yozish uchun maxsus **Note / Javob maydoni**.

### 2.2 Avtomatik Saqlash va To'liq Metrikalar Hisobi
*   **Avtomatik saqlash (Autosave):** Har 15 soniyada ishtirokchi yozayotgan kod va note maydoni bazaga saqlanadi.
*   **Vaqt va harakat kuzatuvi:**
    *   `entered_at` — sessiyaga kirgan vaqti.
    *   `typing_started_at` — klaviaturada ilk marta yozishni boshlagan aniq vaqti.
    *   `submitted_at` — javob yuborilgan vaqt.
    *   `time_spent_secs` — sarflangan aniq vaqt (soniyalarda).
    *   Ishtirokchi o'z vaqtida yuborishga ulgurmasa ham, yozgan harakatlari va sarflagan vaqti yo'qolmaydi (`auto_submitted`).

### 2.3 Yechimlarni Yagona ZIP Arxiv Qilib Yuklab Olish (Admin)
*   Admin panelda har bir challenge kartasida **"📦 ZIP"** tugmasi mavjud.
*   Tugma bosilganda barcha ishtirokchilarning topshirgan yechimlari bitta ZIP arxiv fayl sifatida yuklanadi.
*   ZIP arxiv ichidagi har bir fayl quyidagi tuzilishga ega:
    ```
    PYCHALLENGE SUBMISSION
    ============================================================
    FOYDALANUVCHI: ali (ali@example.com)
    KUN: Day 1 - Kirish va Sikllar
    SAVOL: Fibonachchi ketma-ketligi
    SAVOL TURI: Amaliy (Practical)
    QIYINLIK: medium
    ============================================================
    SAVOL MATNI:
    Fibonachchi sonlarining dastlabki n ta elementini qaytaruvchi funksiya yozing...
    ============================================================
    SESSIYAGA KIRISH: 2026-09-14 17:00:00 UTC
    YOZISHNI BOSHLASH: 2026-09-14 17:01:23 UTC
    YUBORISH VAQTI: 2026-09-14 17:15:40 UTC
    SARFLANGAN VAQT: 940 soniya
    QOIDABUZARLIKLAR: 0
    ============================================================
    YECHIM (KOD):
    def fibonacci(n):
        ...
    ```

### 2.4 AI Agent Orqali Baholash va Excel Import Tizimi
Admin yuklab olingan ZIP arxivni AI agentga (ChatGPT, Claude, Gemini) berib, ishtirokchilarni ko'p parametrli tahlil qilishi mumkin:
1.  **Yondashuv to'g'riligi (Approach)** — 25 ball
2.  **Yechim to'g'riligi (Correctness)** — 35 ball
3.  **Yechish tezligi (Speed)** — 15 ball
4.  **Kod sifati va tushunarli mantiq (Code Quality)** — 15 ball
5.  **Harakat / Qoidabuzarlik yo'qligi (Effort)** — 10 ball
    *   *(Jami: 100 ball)*

AI agent chiqarib bergan natijalar Excel fayl (`.xlsx`) ko'rinishida saqlanadi va Admin paneldagi **"🤖 AI Baholash"** sahifasiga Drag & Drop orqali yuklanadi. Tizim natijalarni darhol bazaga yozadi va umumiy AI Leaderboard shakllantiradi.

---

## 3. Loyihani Ishga Tushirish Qadamlari

### 3.1. Dastlabki Talablar
Tizimda **Docker Desktop** ishlab turgan bo'lishi kerak.

### 3.2. Konteynerlarni Ishga Tushirish
Loyiha papkasida (`c:\projects\chlg1`):
```bash
docker compose up -d
```
Barcha 4 ta xizmat ishga tushadi:
*   `challenge_backend` (FastAPI: port 8000)
*   `challenge_frontend` (React + Nginx)
*   `challenge_nginx` (Reverse Proxy: port 80)
*   `challenge_postgres` (PostgreSQL: port 5434)

### 3.3. Ma'lumotlar Bazasini Migratsiya Qilish
Yangi maydonlar va jadvallarni bazaga qo'llash uchun:
```bash
docker compose exec backend alembic upgrade head
```

### 3.4. Dastlabki Admin Akkauntini Yaratish
```bash
docker compose exec backend python seed_admin.py
```
*Standart admin login ma'lumotlari:*
*   **Email:** `admin@pychallenge.uz`
*   **Parol:** `admin123`

---

## 4. Foydalanish Qo'llanmasi

1.  **Saytga kirish:** Brauzeringizda `http://localhost` manzilini oching.
2.  **Admin bo'lib kirish:** `admin@pychallenge.uz` va `admin123` bilan tizimga kiring.
3.  **Yangi Challenge va Savollar yaratish:**
    *   Admin panelda Challenge yarating.
    *   Kun qo'shing va kunga savol qo'shishda **"Nazariy"** yoki **"Amaliy"** turini tanlang.
    *   Challenge ni **"Faollashtirish"** qiling.
4.  **Ishtirokchilar topshirishi:**
    *   Foydalanuvchilar kirib o'zlariga berilgan savolni yechadilar (kod yozadilar va/yoki note maydonida o'z mantiqlarini izohlaydilar).
5.  **ZIP yuklab olish va Baholash:**
    *   Admin panelda challenge kartasidagi **"📦 ZIP"** tugmasini bosing.
    *   Yuklangan fayllarni AI agentga berib baholang va Excel jadvalini oling.
    *   **"🤖 AI Baholash"** sahifasiga kirib Excel faylni yuklang va natijalarni ko'ring.
