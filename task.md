# Python Challenge Platformasi — To'liq Vazifalar Ro'yxati
> Bu tasklar to'liq bajarilsa, loyiha ishga tushirishga tayyor bo'ladi.

---

## 📁 Bosqich 0 — Loyiha Tuzilishi
- `[x]` `backend/` va `frontend/` papkalar yaratish
- `[x]` `backend/.env` fayl yaratish
- `[x]` `backend/requirements.txt` yozish
- `[x]` `backend/app/__init__.py` yaratish
- `[x]` `backend/app/db/__init__.py` yaratish
- `[x]` `backend/app/models/__init__.py` yaratish
- `[x]` `backend/app/routers/__init__.py` yaratish
- `[x]` `backend/app/schemas/__init__.py` yaratish
- `[x]` `backend/app/services/__init__.py` yaratish
- `[x]` `docker-compose.dev.yml` yaratish (postgres dev)

---

## 🗄️ Bosqich 1 — Ma'lumotlar Bazasi
- `[x]` SQLAlchemy async ulanish (`database.py`)
- `[x]` Barcha modellar yozilgan (`models.py`) — 9 ta jadval
- `[x]` Alembic o'rnatish va sozlash
- `[x]` Birinchi migratsiya yaratish (`initial_schema`)
- `[x]` Migratsiyani ishga tushirish — barcha jadvallar bazada ✅

---

## 🔐 Bosqich 2 — Auth (Backend)
- `[x]` `app/schemas/auth.py` — Pydantic schemalar (RegisterRequest, LoginRequest, TokenResponse)
- `[x]` `app/core/security.py` — parol xeshlash, JWT yaratish, `get_current_user` middleware
- `[x]` `app/routers/auth.py` — 4 ta endpoint:
  - `[x]` `POST /api/v1/auth/register`
  - `[x]` `POST /api/v1/auth/login`
  - `[x]` `POST /api/v1/auth/forgot-password`
  - `[x]` `POST /api/v1/auth/reset-password`
- `[x]` `app/core/email.py` — Email yuborish funksiyasi (parol tiklash havolasi, HTML shablon)
- `[x]` Auth routerlarni `main.py` ga ulash

---

## 🛠️ Bosqich 3 — Admin API (Backend)
- `[x]` `app/schemas/admin.py` — Admin schemalar
- `[x]` `app/routers/admin.py` — Admin endpointlar:
  - `[x]` `POST /api/admin/challenges` — Challenge yaratish
  - `[x]` `PUT /api/admin/challenges/{id}` — Tahrirlash
  - `[x]` `POST /api/admin/challenges/{id}/activate` — Faollashtirish
  - `[x]` `POST /api/admin/days` — Kun qo'shish (name + time_limit)
  - `[x]` `POST /api/admin/questions` — Savol qo'shish (SVG + test cases JSONB)
  - `[x]` `DELETE /api/admin/questions/{id}` — Savol o'chirish
  - `[x]` `GET /api/admin/challenges/{id}/stats` — Statistika
- `[x]` Admin rolini tekshirish (`is_admin` flag `users` jadvalida)
- `[x]` Admin routerlarni `main.py` ga ulash

---

## 🧠 Bosqich 4 — Imtihon Mexanizmi (Backend)
- `[x]` `app/schemas/session.py` — Session schemalar
- `[x]` Random savol tayinlash logikasi (`session.py` ichida):
  - `[x]` Bir xil kunning savollaridan random birini tanlash
  - `[x]` `user_question_assignments` ga yozish (UNIQUE constraint himoyasi)
- `[x]` `app/routers/session.py` — Session endpointlar:
  - `[x]` `POST /api/v1/days/{id}/enter` — Kunga kirish:
    - Tayinlov bor/yo'qligini tekshirish
    - Yo'q bo'lsa random savol tayinlash
    - Sessiya yaratish (`expires_at = now + time_limit`)
    - Response: `{session_id, expires_at, question_svg, starter_code}`
  - `[x]` `PATCH /api/v1/sessions/{id}/typing-start` — Birinchi klavish vaqtini saqlash
  - `[x]` `PATCH /api/v1/sessions/{id}/autosave` — Kodni 30s da bir saqlash
  - `[x]` `POST /api/v1/sessions/{id}/violation` — Buzilish qayd etish:
    - `violations_count++`
    - Agar `>= max_violations` → status = `disqualified`
  - `[x]` `POST /api/v1/sessions/{id}/submit` — Kod yuborish
- `[x]` Kun ochilish logikasi: `challenge.start_date + day_number - 1 == bugun`

---

## 🐳 Bosqich 5 — Docker Sandbox (Kod Baholash)
- `[x]` `app/services/sandbox_service.py` — Docker orqali kod ijrosi:
  - `[x]` Test kodni `/tmp/{session_id}/solution.py` ga yozish
  - `[x]` `docker run --rm --network none --memory=128m --cpus=0.5 --pids-limit=50 --read-only` bilan ishga tushirish
  - `[x]` 5 soniyalik asyncio timeout (SIGKILL)
  - `[x]` Natijani test keyslar bilan solishtirib ball hisoblash (o'tgan test % * 10)
  - `[x]` `submissions` jadvaliga yozish
  - `[x]` `users.total_score` yangilash

---

## ⏰ Bosqich 6 — Avtomatik Jarayonlar (Backend)
- `[x]` `app/core/background_tasks.py`:
  - `[x]` **Avto-Submit cron** — har 1 daqiqada `expires_at < now` bo'lgan faol sessiyalarni topib, `final_code` ni yuborish
  - `[x]` **Challenge tugash cron** — `end_date` o'tgan challengelar uchun `challenge_results` ni hisoblash, g'olibni aniqlash
- `[x]` Background taskni `main.py` startup event ga ulash
- `[x]` Leaderboard finalize endpoint (`POST /challenges/{id}/finalize`) — admin tomonidan chaqiriladi

---

## ⚛️ Bosqich 7 — Frontend: Asosiy Tuzilish
- `[x]` `cd frontend && npm create vite@latest . -- --template react`
- `[x]` Kerakli paketlarni o'rnatish:
  - `[x]` `npm install react-router-dom axios zustand`
  - `[x]` `npm install @monaco-editor/react`
  - `[x]` `npm install react-hot-toast`
- `[x]` `src/api/client.js` — Axios instance (baseURL + JWT interceptor)
- `[x]` `src/store/authStore.js` — Zustand auth state (user, token, login/logout)
- `[x]` `src/App.jsx` — React Router (public va himoyalangan routelar)
- `[x]` Global CSS (`src/index.css`) — dizayn tizimi, fontlar, ranglar

---

## 🎨 Bosqich 8 — Frontend: Auth Sahifalari
- `[x]` `src/pages/Login.jsx` — Email + parol kirish formasi
- `[x]` `src/pages/Register.jsx` — Ro'yxatdan o'tish formasi
- `[x]` `src/pages/ForgotPassword.jsx` — Parolni tiklash (email kiritish)
- `[x]` `src/pages/ResetPassword.jsx` — Yangi parol o'rnatish (token bilan)
- `[x]` `src/components/ProtectedRoute.jsx` — Auth bo'lmasa login ga yo'naltirish

---

## 🗺️ Bosqich 9 — Frontend: Foydalanuvchi Paneli
- `[x]` `src/pages/Dashboard.jsx` — Bosh sahifa: faol challengelar ro'yxati
- `[x]` `src/pages/ChallengeRoadmap.jsx` — 30 kunlik yo'l xaritasi:
  - `[x]` Har bir kun kartasi (locked / open / completed / today)
  - `[x]` Har kun uchun foydalanuvchining bali (ertasi kuni ko'rinadi)
- `[x]` `src/pages/Results.jsx` — Challenge natijalar sahifasi (faqat tugagandan keyin)
- `[x]` `src/components/Navbar.jsx` — Navigatsiya
- `[x]` `src/components/CountdownTimer.jsx` — Challenge boshlanishigacha sanash

---

## 🏟️ Bosqich 10 — Frontend: Imtihon Arenasi (Lockdown)
- `[x]` `src/pages/Arena.jsx` — Asosiy imtihon sahifasi:
  - `[x]` Sahifa yuklanishida `requestFullscreen()` chaqirish
  - `[x]` `fullscreenchange` va `visibilitychange` eventlarni tutish
  - `[x]` Violation modal komponenti (ogohlantirish)
  - `[x]` Diskvalifikatsiya modali
- `[x]` `src/hooks/useAntiCheat.js`:
  - `[x]` Fullscreen chiqish → violation qayd etish → 3 ta bo'lsa exit
  - `[x]` Tab almashtirish (`visibilitychange`) → violation
  - `[x]` Ctrl+V bloklash
  - `[x]` Keystroke tezligi tekshiruvi (>650 belgi/min → violation)
  - `[x]` Multi-monitor aniqlash (`screen.width > window.innerWidth * 1.5`)
  - `[x]` F12 (DevTools) ochishni bloklash
- `[x]` `src/hooks/useTimer.js`:
  - `[x]` `expires_at` dan hisoblash (serverdan keladi)
  - `[x]` Vaqt tugaganda avto-submit va oynani yopish
- `[x]` `src/hooks/useAutosave.js` — Kodni 30 soniyada bir backendga saqlash
- `[x]` Monaco Editor (savol SVG ko'rinishi + kod yozish qismi)
- `[x]` "Yuborish" tugmasi → kodni backendga yuborish → natijani ko'rsatish

---

## 👑 Bosqich 11 — Frontend: Admin Panel
- `[x]` `src/pages/admin/AdminDashboard.jsx` — Statistika va challengelar ro'yxati
- `[x]` `src/pages/admin/ChallengeForm.jsx` — Yangi challenge yaratish/tahrirlash:
  - `[x]` Nom, tavsif, kun soni, boshlanish sanasi, mukofot
  - `[x]` "Faollashtirish" tugmasi
- `[x]` `src/pages/admin/DayManager.jsx` — Kunlarni boshqarish (sarlavha, vaqt limiti)
- `[x]` `src/pages/admin/QuestionForm.jsx` — Savol qo'shish:
  - `[x]` SVG savol matni kiritish (yoki SVG preview)
  - `[x]` Qiyinlik darajasi
  - `[x]` Starter kod
  - `[x]` Test keyslar (input → expected output) qo'shish
- `[x]` Admin routelarni `App.jsx` ga qo'shish

---

## 🚀 Bosqich 12 — Ishga Tushirish (Deployment)
- `[x]` `docker-compose.yml` to'liq yozildi:
  - `[x]` `postgres` servisi (volume bilan)
  - `[x]` `backend` servisi (`uvicorn app.main:app`)
  - `[x]` `frontend` servisi (nginx + build)
  - `[x]` `sandbox-runner` (Docker socket mount orqali)
- `[x]` `backend/Dockerfile` yozildi
- `[x]` `frontend/Dockerfile` yozildi (multi-stage: build + nginx)
- `[x]` `nginx/nginx.conf` — reverse proxy (frontend → /, backend → /api/)
- `[x]` `.env.production` — muhit o'zgaruvchilari shabloni
- `[x]` `docker compose up -d` bilan ishga tushirish
- `[x]` `alembic upgrade head` migratsiya (container ichida yoki tashqarida)
- `[x]` Birinchi admin foydalanuvchini qo'shish (seed script)
- `[x]` Barcha endpointlarni `curl` bilan sinash

---

## ✅ Bosqich 13 — Yakuniy Tekshiruv
- `[x]` Ro'yxatdan o'tish → kirish → challenge ko'rish → kunni boshlash → kod yozish → yuborish oqimi sinash
- `[x]` Anti-cheat: fullscreen chiqsa violation, 3 marta → diskvalifikatsiya
- `[x]` Avto-submit: vaqt tugasa kod saqlanib yuborilishini sinash
- `[x]` Admin: challenge yaratish → kun qo'shish → savol qo'shish → faollashtirish
- `[x]` Challenge tugash croni → leaderboard to'g'ri hisoblanishini sinash
- `[x]` Ko'p foydalanuvchi: 2 ta akaunt, bir xil kunda boshqa-boshqa savol kelishini tekshirish
