# Ko'chatim — Loyiha To'liq Hujjati

> Ko'chatim — ko'chat bog'bonlari uchun inventar va sotuv boshqaruv tizimi.
> Foydalanuvchilar ko'chatlarini guruh va sort bo'yicha yuritadi, sotuvlarni kuzatadi,
> boshqa bog'bonlar bilan hamkorlik qiladi.

---

## Loyiha arxitekturasi (umumiy ko'rinish)

```
Kochatim/
├── backend/        — Python (Flask) REST API server
├── client/         — React web-ilova (boshqaruv paneli, klient sayti)
├── miniApp/        — Telegram Mini App (React, faqat kirish sahifasi)
└── bot/            — Telegram bot (Aiogram 2.x)
```

Barcha qismlar bitta umumiy `backend` bilan ishlaydi. Foydalanuvchi:

1. **Telegram botga** `/start` yozadi → bot telefon raqamini so'raydi
2. **Mini App**ni ochadi → avtomatik kiradi → kochatim.uz'ga yo'naltiriladi
3. **Web-saytda** 6 raqamli OTP kodi kiritadi → session oladi → panelda ishlaydi

---

## 1. BACKEND (`backend/`)

### Texnologiyalar va sabablar

| Kutubxona | Versiya | Nega ishlatilgan |
|-----------|---------|-----------------|
| **Flask** | 3.0.3 | Yengil va tez Python web framework. Micro-framework — faqat kerakli narsa ulash mumkin |
| **psycopg2-binary** | 2.9.11 | PostgreSQL bilan ishlash uchun. Binary versiya — C extension'ni alohida o'rnatish shart emas |
| **python-dotenv** | 1.0.1 | `.env` faylidan muhit o'zgaruvchilarini o'qish. Secret'larni kod ichiga yozmaslik uchun |
| **gunicorn** | 23.0.0 | Production WSGI server. Flask'ning built-in serveri production'ga yaramaydi |
| **requests** | 2.32.3 | HTTP so'rovlar: Telegram API, ImgBB, ip-api.com ga murojaat uchun |

**PostgreSQL** ma'lumotlar bazasi sifatida ishlatiladi. SQLite emas, chunki:
- Ko'p foydalanuvchi parallel ishlaganda lock muammosi yo'q
- `SERIAL`, `RETURNING`, lateral JOIN, `ON CONFLICT DO UPDATE` kabi qulay SQL xususiyatlari bor
- Production deployment uchun standart tanlov

---

### `backend/app.py` — Asosiy kirish nuqtasi

**Nima qiladi:** Flask ilovasini yaratadi, barcha qismlarni birlashtiradi va ishga tushiradi.

**Qachon ishlaydi:** Server ishga tushganda birinchi bajariladi.

**Nima vazifa bajaradi:**
- `create_app()` funksiyasi orqali Flask ilovasini sozlaydi
- `init_pool()` → ma'lumotlar bazasiga ulanishlar havzasini yaratadi
- `init_db()` → DB jadvallarini yaratadi (agar mavjud bo'lmasa)
- `auth_bp` va `api_bp` blueprint'larini ro'yxatdan o'tkazadi
- `/health` endpoint — server ishlayotganini tekshirish uchun
- **CORS** (Cross-Origin Resource Sharing) sozlaydi:
  - Faqat ruxsat etilgan domenlardan so'rovlar qabul qilinadi: `kochatim.uz`, `app.kochatim.uz`, `localhost:5173`
  - `OPTIONS` preflight so'rovlarini ham boshqaradi
  - `Credentials: true` — cookie/Authorization header bilan ishlash uchun

---

### `backend/config.py` — Konfiguratsiya

**Nima qiladi:** `.env` faylidan barcha sozlamalarni o'qib, bir joyda saqlaydi.

```
DATABASE_URL      — PostgreSQL ulanish manzili
API_KEY           — Bot → Backend aloqasi uchun maxfiy kalit
BOT_TOKEN         — Telegram bot tokeni
TG_BOT_USERNAME   — Bot username (hamkorlik linki uchun)
IMGBB_API_KEY     — Rasm yuklash servisi kaliti
OTP_TTL_SECONDS   — OTP kodi amal qilish muddati (standart: 120 sekund)
SESSION_TTL_SECONDS — Session muddati (standart: 30 kun)
DB_POOL_MIN/MAX   — DB ulanishlar havzasi chegaralari
FLASK_ENV         — production / development
```

---

### `backend/extensions.py` — DB ulanishlar havzasi (Connection Pool)

**Nima qiladi:** PostgreSQL ulanishlarni samarali boshqaradi.

**Nega connection pool?**
Har bir so'rovda yangi ulanish ochish sekin (150-300ms). Pool esa 1-20 ta ulanishni saqlab turadi. So'rov kelganda mavjud ulanish beriladi, tugagach qaytariladi.

**Asosiy funksiyalar:**
- `init_pool()` — `ThreadedConnectionPool` yaratadi (bir vaqtda bir necha thread ishlasa ham xavfsiz)
- `get_conn()` — pooldan ulanish oladi
- `put_conn(conn, close=False)` — ulanishni poolga qaytaradi. `close=True` bo'lsa — yo'q qiladi (buzilgan ulanish uchun)

---

### `backend/db.py` — Ma'lumotlar bazasi yordamchi funksiyalari

**Nima qiladi:** SQL so'rovlarni bajarish uchun qulay wrapper. To'g'ridan-to'g'ri psycopg2 bilan ishlash o'rniga, barcha joyda bir xil usulda DB bilan muloqot qilish imkonini beradi.

**Nega retry mexanizmi?** PostgreSQL vaqti-vaqti bilan ulanishni uzishi mumkin (SSL timeout, server restart). Birinchi marta xato bo'lsa, buzilgan ulanish tashlanib, yangi ulanish bilan qayta uriniladi.

| Funksiya | Nima qaytaradi | Qachon ishlatiladi |
|----------|----------------|-------------------|
| `execute(query, params)` | `None` | INSERT, UPDATE, DELETE |
| `execute_returning(query, params)` | `Dict` yoki `None` | `RETURNING` li INSERT |
| `fetch_one(query, params)` | `Dict` yoki `None` | Bitta satr SELECT |
| `fetch_all(query, params)` | `List[Dict]` | Ko'p satr SELECT |

**SQL injection himoyasi:** Barcha qiymatlar `%s` placeholder orqali uzatiladi, hech qachon f-string bilan SQL ichiga qo'shilmaydi.

---

### `backend/db_init.py` — Jadvallarni yaratish

**Nima qiladi:** Server ishga tushganda barcha kerakli DB jadvallarini yaratadi.

**Qachon ishlaydi:** Har gal server start bo'lganda (lekin `IF NOT EXISTS` tufayli idempotent).

**Jadvallar:**

| Jadval | Vazifasi |
|--------|----------|
| `users` | Foydalanuvchilar: Telegram ID, ism, telefon, username, yosh, foto |
| `categories` | Ko'chat guruhlari (masalan: "Mevali", "Terak") |
| `types` | Ko'chat sortlari (masalan: "Olma — Fuji"). Kategoriyaga tegishli |
| `seedlings` | Inventar: har bir sort bo'yicha 1-nav, 2-nav, 3-nav soni |
| `seedlings_logs` | Inventar o'zgarish tarixi (kim, qachon, qancha o'zgartirdi) |
| `img` | Sort rasmlari. `i_url` — ImgBB URL yoki Telegram file_id |
| `sales` | Sotuvlar: qaysi sort, qancha sotildi, narxi |
| `login_codes` | OTP kodlari (hash saqlanadi, kod emas) |
| `sessions` | Faol sessiyalar: token hash, qurilma nomi, IP, shahar |
| `partners` | Hamkorlar juftlari (A↔B simmetrik: ikki satr) |
| `partner_invites` | Hamkorlik takliflari (Telegram deep-link tokeni) |

**Trigger:** `update_modified_column()` — har bir UPDATE da `updated_at` avtomatik yangilanadi.

**Indekslar:** `categories`, `types`, `seedlings`, `sales`, `sessions` jadvallariga tezlashtirish uchun `u_id`, `t_id`, `c_id` bo'yicha indekslar qo'shilgan.

---

### `backend/auth/` — Autentifikatsiya

#### `auth/__init__.py`
`/auth/*` prefix bilan Blueprint yaratadi. Uch moduli import qiladi.

#### `auth/otp.py` — OTP orqali kirish

**Qanday ishlaydi:**
1. **Bot** → `POST /auth/request-code` chaqiradi (API KEY bilan)
   - Foydalanuvchi DB ga saqlanadi (UPSERT)
   - 6 raqamli tasodifiy kod generatsiya qilinadi (`secrets.randbelow`)
   - Kodning SHA-256 hashi DB ga saqlanadi (kod emas, hash!)
   - Kod botga qaytariladi → bot foydalanuvchiga yuboradi
2. **Web sayt** → `POST /auth/verify-code` chaqiradi
   - Kiri kodning hashi hisoblanadi, DB da qidiriladi
   - Eskirganmi? Ishlatilganmi? — tekshiriladi
   - Hammasi to'g'ri → 32 baytli `session_token` generatsiya qilinadi
   - Token hashi DB ga saqlanadi → token foydalanuvchiga yuboriladi

**`_insert_session()`:** Sessiya yaratganda qurilma nomi va shahar ham saqlanadi. Agar foydalanuvchida 3 tadan ortiq sessiya bo'lsa — eskisi o'chiriladi.

#### `auth/telegram_webapp.py` — Telegram Mini App orqali kirish

**Qanday ishlaydi:**
1. Mini App `window.Telegram.WebApp.initData` ni serverga yuboradi
2. Server `telegram_webapp_verify()` orqali bu ma'lumotni Telegram bot token yordamida tekshiradi (HMAC-SHA256 imzo)
3. Haqiqiy bo'lsa → session yaratiladi, `is_registered` (telefon raqami bormi?) qaytariladi

#### `auth/user_id_login.py` — Telegram ID orqali to'g'ridan-to'g'ri kirish

**Qanday ishlaydi:** u_id bilan to'g'ridan-to'g'ri session yaratadi. Faqat ma'lum holatlarda ishlatiladi (test yoki admin).

---

### `backend/middleware/` — Himoya qatlamlari

#### `middleware/require_session.py`
`Authorization: Bearer <token>` header ni tekshiradi. Token hashi DB da topilsa va muddati o'tmagan bo'lsa — `g.u_id` va `g.token_hash` o'rnatadi. Keyin endpoint o'z ishini qiladi.

#### `middleware/require_api_key.py`
`X-API-KEY` header ni Config.API_KEY bilan solishtiradi. Faqat bot va server-server aloqa uchun.

**Nima uchun ikki xil himoya?**
- Session → web foydalanuvchilar (browser orqali kiradi)
- API Key → bot backend (mashinalar orasidagi muloqot)

---

### `backend/api/` — REST API endpointlar

#### `api/__init__.py`
`/api/*` prefix bilan Blueprint. Barcha API modullari shu yerda import qilinadi.

#### `api/users.py` — Foydalanuvchilar

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| GET | `/api/me` | Session | Joriy foydalanuvchi ma'lumotlari |
| POST | `/api/users/ensure` | API Key | Foydalanuvchini yaratadi yoki yangilaydi (bot uchun) |
| GET | `/api/users/<u_id>` | API Key | Biror foydalanuvchi ma'lumotlari |
| GET | `/api/gardeners` | Ochiq | Bog'bonlarni qidirish (ism, username, ID bo'yicha) |

#### `api/categories.py` — Ko'chat guruhlari

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| GET | `/api/categories/by-user?u_id=` | API Key | Bot uchun kategoriyalar ro'yxati |
| POST | `/api/categories` | API Key | Yangi kategoriya yaratish (bot) |
| GET | `/api/categories` | Session | Mening kategoriyalarim |
| POST | `/api/categories/me` | Session | Yangi kategoriya (web) |
| PUT | `/api/categories/<c_id>` | API Key | Kategoriya nomini o'zgartirish |
| DELETE | `/api/categories/<c_id>` | API Key | Kategoriyani o'chirish |

#### `api/seedlings.py` — Ko'chat inventari

**Muhim:** Ko'chatlar 3 navga bo'linadi (quality_1, quality_2, quality_3).

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| GET | `/api/seedlings/count?u_id=&t_id=` | API Key | Sort bo'yicha inventar soni |
| POST | `/api/seedlings/set` | API Key | Inventar qo'shish (bot) |
| GET | `/api/seedlings?t_id=` | Session | Web: inventar ko'rish |
| POST | `/api/seedlings/update` | Session | Web: inventar o'zgartirish |

`/seedlings/update` manfiy songa tushishni oldini oladi (`INSUFFICIENT_STOCK` xatosi).
Har bir o'zgarish `seedlings_logs` jadvaliga yoziladi.

#### `api/sales.py` — Sotuvlar

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| POST | `/api/sales` | API Key | Sotuv qo'shish (bot). Inventardan avtomatik ayiradi |
| GET | `/api/sales` | Session | Sotuvlar tarixi + kategoriya bo'yicha pie grafik |

Sotuv qo'shishda: ownership tekshiriladi (t_id bu u_id galigini), yetarli inventar bormi tekshiriladi, so'ng `sales` ga qo'shib, `seedlings` dan ayiradi.

#### `api/images.py` — Rasmlar

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| POST | `/api/img` | API Key | Bot: sort rasmi qo'shish (Telegram file_id) |
| POST | `/api/img/upload` | Session | Web: to'g'ridan-to'g'ri rasm yuklash |
| GET | `/api/img/by-type?t_id=` | API Key | Bot: sort rasmi URL |
| GET | `/api/img/<file_id>` | Ochiq | Telegram rasmini proxy qiladi (browser uchun) |

**Rasm oqimi:** Telegram foydalanuvchi bot orqali rasm yuboradi → `file_id` keladi → `process_image_input()` uni ImgBB ga yuklaydi va URL qaytaradi → URL DB da saqlanadi. Web'da rasm ko'rsatilganda agar `file_id` bo'lsa `/api/img/<file_id>` proxy endpoint orqali Telegram serveridan to'g'ridan-to'g'ri yuklaydi.

#### `api/dashboard.py` — Boshqaruv paneli ma'lumotlari

**`GET /api/me/dashboard`** — Joriy foydalanuvchining barcha ma'lumotlari bir so'rovda.

**Qanday ishlaydi:**
1. 60 soniyalik cache tekshiriladi → mavjud bo'lsa qaytariladi
2. `ThreadPoolExecutor` yordamida 5 ta so'rov **parallel** bajariladi:
   - `get_user()` — foydalanuvchi ma'lumotlari
   - `get_categories()` — kategoriyalar
   - `get_types()` — sortlar (so'nggi rasm bilan, `LATERAL JOIN`)
   - `get_seedlings()` — inventar
   - `get_sales_summary()` — sotuvlar yig'indisi
3. Barcha natijalar birlashtiriladi va cache ga saqlanadi

**Nega parallel?** 5 ta ketma-ket so'rov ~150ms bo'lsa, parallel ~50ms da tugaydi.

**`GET /api/users/<u_id>/dashboard`** — Boshqa bog'bonning ochiq profili (inventar ko'rish). Autentifikatsiya talab qilinmaydi.

#### `api/partners.py` — Hamkorlar

Hamkorlik simmetrik: A B bilan hamkor bo'lsa, DB da ikkita satr bor: (A, B) va (B, A).

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| GET | `/api/partners` | Session | Mening hamkorlarim ro'yxati |
| POST | `/api/partners/remove` | Session | Hamkorni o'chirish (Telegram xabari yuboriladi) |
| GET | `/api/partners/invite-token` | Session | Taklifnoma tokeni olish |
| GET | `/api/users/<u_id>/partners` | API Key | Bot: foydalanuvchi hamkorlari |
| POST | `/api/partners/accept` | API Key | Bot: taklifni qabul qilish |
| POST | `/api/partners/decline` | API Key | Bot: taklifni rad etish |

**Hamkorlik oqimi:**
1. A "Hamkor qo'shish" tugmasini bosadi → `invite-token` yaratiladi (7 kunlik)
2. A Telegram deep-link'ni `t.me/BotNomi?start=partner_TOKEN` bo'lib B ga yuboradi
3. B linkni bosadi → bot `partner_TOKEN` ni taniydi → `accept` API chaqiradi
4. Ikki tomonga ham hamkor qo'shiladi + Telegram xabari yuboriladi

#### `api/sessions.py` — Sessiyalar (qurilmalar)

| Method | URL | Himoya | Vazifasi |
|--------|-----|--------|----------|
| GET | `/api/sessions` | Session | Barcha faol sessiyalar (qurilmalar) ro'yxati |
| DELETE | `/api/sessions/<session_id>` | Session | Qurilmani o'chirish |

Joriy sessiya `is_current: true` bilan belgilanadi va o'chirib bo'lmaydi.

---

### `backend/utils/` — Yordamchi funksiyalar

#### `utils/security.py`
- `generate_otp_6()` — 6 raqamli tasodifiy OTP (`secrets.randbelow` — kriptografik xavfsiz)
- `sha256_hex(value)` — SHA-256 hash (tokenlar DBda hash sifatida saqlanadi)
- `generate_token(32)` — URL-safe random token (session token)
- `generate_invite_token()` — Telegram deep-link uchun URL-safe token (24 belgi)
- `safe_equal(a, b)` — `hmac.compare_digest` — timing attack'dan himoya
- `telegram_webapp_verify(init_data, bot_token)` — HMAC-SHA256 bilan initData ni tekshiradi

**Nega hash saqlanadi?** Agar DB sizib chiqsa ham, haqiqiy token noma'lum qoladi.

#### `utils/cache.py`
60 soniyalik xotiradagi (in-process) cache. Dashboard ma'lumotlarini DB ga har so'rovda murojaat qilmasdan qaytaradi.

**Cheklov:** Gunicorn ko'p worker rejimida har worker o'z nusxasini saqlaydi. Kelajakda Redis bilan almashtirilishi mumkin.

#### `utils/device.py`
- `parse_device(user_agent)` — User-Agent'dan qurilma nomi chiqaradi: `"Chrome macOS"`, `"Safari iPhone"`
- `get_city(ip)` — `ip-api.com` dan bepul geolokatsiya (shahar nomi)
- `get_client_ip(request)` — `X-Forwarded-For` headerdan haqiqiy IP oladi (proxy orqasida bo'lsa ham)

#### `utils/telegram_notify.py`
`send_message(chat_id, text)` — Telegram Bot API orqali xabar yuboradi. Xato bo'lsa jimgina o'tadi (ilovani to'xtatmaydi).

#### `utils/images_v2.py`
- `upload_to_imgbb(bytes)` — binary rasmni ImgBB'ga base64 orqali yuklaydi, URL qaytaradi
- `telegram_to_imgbb(file_id)` — Telegram file_id → binary yuklab → ImgBB ga yuklaydi
- `process_image_input(val)` — agar URL kelsa qaytaradi, agar Telegram ID kelsa ImgBB'ga o'tkazadi

#### `utils/time.py`
UTC vaqt bilan ishlash: `utcnow()`, `utc_in_seconds(n)`, `naive_utc()`. PostgreSQL `TIMESTAMP WITHOUT TIMEZONE` bilan mos ishlash uchun.

#### `utils/errors.py`
```python
ok(data)   → {"ok": True, "data": data}
fail(msg)  → {"ok": False, "error": {"message": msg, "code": ...}}
```
Barcha endpointlar bir xil formatda javob qaytaradi.

---

## 2. CLIENT — Web Ilova (`client/`)

### Texnologiyalar

| Kutubxona | Versiya | Nega ishlatilgan |
|-----------|---------|-----------------|
| **React** | 19.0 | Komponent asosida UI yaratish. State boshqarish oson |
| **Vite** | 6.0 | Ultra-tez dev server va build tool. Create React App dan 10-20x tez |
| **React Router DOM** | 7.1 | Sahifalar orasida navigatsiya. URL → komponent mosligi |
| **Recharts** | 3.6 | Pie diagrammalar. React uchun qulay, SVG asosida |
| **Axios** | 1.7 | HTTP kutubxona (miniApp da ishlatiladi) |
| **Lucide React** | 0.473 | SVG ikonlar. Bir xil dizayn tili uchun |
| **Sass** | 1.97 | CSS preprocessor. Variables, nesting, mixins imkoni |

---

### `client/src/main.jsx` — Kirish nuqtasi
React ilovasini `<div id="root">` ga render qiladi.

### `client/src/App.jsx` — Marshrutlash

```
/                        → Home (ochiq, login shart emas)
/login                   → Login sahifasi
/gardeners/:uId          → Bog'bon profili (ochiq)
/gardeners/:uId/group/:cId → Guruhi bilan profil
/dashboard               → [Auth kerak] Boshqaruv paneli
/u/:uId/inventory        → [Auth kerak] Inventar
/sales                   → [Auth kerak] Sotuvlar
/settings                → [Auth kerak] Sozlamalar
```

`ThemeProvider` va `DashboardProvider` butun ilovani o'raydi.
`TelegramHandler` komponentasi URL parametrdan OTP kodi bilan session yaratadi.

### `client/src/api/https.js` — HTTP qatlami

- `API_BASE` — `VITE_API_BASE_URL` muhit o'zgaruvchisidan olinadi
- `getSessionToken()` — `localStorage`'dan token oqadi
- `apiFetch(path, options)` — markaziy HTTP funksiya:
  - Avtomatik `Authorization: Bearer <token>` qo'shadi
  - JSON va FormData ikkisini ham qo'llab-quvvatlaydi
  - `401` kelsa — token o'chiriladi (avtomatik logout)
  - `data.ok !== true` bo'lsa — xato tashlaydi

### `client/src/api/endpoints.js`
Barcha API chaqiruvlarini bir joyda saqlaydi (URL'lar tarqoq bo'lmasin).

### `client/src/auth/RequireAuth.jsx`
`localStorage`'da token bor-yo'qligini tekshiradi. Yo'q bo'lsa `/login` ga yo'naltiradi.

### `client/src/context/DashboardContext.jsx` — Global holat boshqaruvi

**Nima qiladi:**
- Dashboard ma'lumotlarini bir marta yuklaydi, barcha sahifalarda ishlatiladi
- 5 daqiqalik client-side cache (har sahifa almashganda qayta yuklamas uchun)
- `refreshDashboard()` — majburiy qayta yuklash (inventar o'zgarganda)
- Sotuvlar uchun ham alohida cache: `salesData`, `fetchSales()`, `refreshSales()`

**Nega Context API?** Redux kabi og'ir kutubxona o'rniga, dashboard data barcha bolalar komponentlarga prop drilling qilmasdan yetkaziladi.

### `client/src/context/ThemeContext.jsx`
Tungi/kunduzgi rejim. `localStorage`'da saqlanadi.

---

### Sahifalar (`client/src/pages/`)

#### `pages/home/Home.jsx` — Bosh sahifa
- Kirish yo'q bo'lsa ham ko'rinadi
- Bog'bonlarni qidirish (250ms debounce bilan)
- Tizimga kirish / Dashboard tugmalari

#### `pages/login/Login.jsx` — Kirish sahifasi
Telegram ID kiritiladi → OTP kodi yuboriladi (bot orqali) → kod kiritiladi → session olinadi.

#### `pages/dashboard/Dashboard.jsx` — Boshqaruv paneli
- Guruhlar ro'yxati + har bir guruh umumiy ko'chat soni
- Pie diagramma: guruhlar bo'yicha ulush
- Guruhga bosing → shu guruh sortlari ko'rinadi (1-nav, 2-nav, 3-nav)
- Kontextdan `dashboardData` oladi — alohida so'rov qilmaydi

#### `pages/inventory/Inventory.jsx` — Inventar boshqaruvi
- Guruh va sort bo'yicha navigatsiya
- Ko'chat qo'shish / ayirish
- Yangi guruh va sort qo'shish modal oynalari
- Rasmlar ko'rsatiladi (ImgBB URL yoki Telegram proxy)

#### `pages/sales/Sales.jsx` — Sotuvlar
- Sotuvlar tarixi jadval ko'rinishida
- Kategoriya bo'yicha pie diagramma (tushum)

#### `pages/gardener/Gardener.jsx` — Bog'bon profili (ochiq)
URL dagi `uId` bo'yicha boshqa bog'bonning ma'lumotlarini ko'rsatadi. Login shart emas.

#### `pages/settings/Settings.jsx` — Sozlamalar
- Profil ma'lumotlari (Telegram'dan olingan)
- Hamkorlar: ro'yxat, qo'shish (invite link), o'chirish
- Qurilmalar: barcha faol sessiyalar, o'chirish
- Tema (tungi/kunduzgi)
- Tizimdan chiqish

---

### Komponentlar (`client/src/components/`)

| Komponent | Vazifasi |
|-----------|---------|
| `Sidebar` | Chap tomongi navigatsiya menyu |
| `Header` | Yuqori panel (asosiy sahifada) |
| `Loader` | Yuklanish animatsiyasi |
| `PieCard` | Recharts asosida qayta ishlatiladigan pie chart |
| `GroupCard` | Inventarda guruh kartochkasi |
| `SortCard` | Inventarda sort kartochkasi (nav miqdori bilan) |
| `AddGroupModal` | Yangi guruh qo'shish modal oynasi |
| `AddTypeModal` | Yangi sort qo'shish modal oynasi |
| `TransactionCard` | Sotuv yozuvi kartochkasi |
| `auth/TelegramHandler` | URL dan OTP parametrini ushlaydi va session yaratadi |

---

## 3. MINIAPP — Telegram Mini App (`miniApp/`)

### `miniApp/src/App.jsx` — Asosiy va yagona komponent

**Qanday ishlaydi:**
1. `window.Telegram.WebApp` mavjudligini tekshiradi
2. `tg.ready()` va `tg.expand()` — Telegram'ga tayyor ekanligini aytadi
3. 500ms kutib `initData` (Telegram imzolagan ma'lumot) oladi
4. `POST /auth/telegram-webapp` ga yuboradi
5. Server session_token qaytaradi → `localStorage`'ga saqlanadi
6. `is_registered: true` → `kochatim.uz/dashboard` ga yo'naltiradi
7. `is_registered: false` → "botga qaytib ro'yxatdan o'ting" ko'rsatadi

**Texnologiyalar:**
- React + Vite (client bilan bir xil)
- `axios` HTTP uchun (client `fetch` ishlatadi)
- Telegram Web App SDK (CDN orqali yoki Telegram beradi)

---

## 4. BOT — Telegram Bot (`bot/`)

**Framework:** Aiogram 2.x (asinxron, Python asyncio asosida)

**Tuzilma:**
```
bot/
├── app.py              — Ishga tushirish, on_startup
├── loader.py           — Bot, dispatcher, storage yaratish
├── data/
│   ├── config.py       — Bot konfiguratsiyasi
│   └── database.py     — Backend API chaqiruv
├── handlers/           — Xabarlarni qayta ishlash
├── keyboards/          — Telegram klaviaturalar
├── filters/            — Maxsus filtrlar
├── middlewares/
│   └── throttling.py   — Spam oldini olish
├── states/
│   └── state_one.py    — FSM holatlari (ro'yxatdan o'tish jarayoni)
├── utils/
│   ├── notify_admins.py — Start'da admin xabari
│   └── set_bot_commands.py — Bot buyruqlarini Telegram'ga ro'yxatdan o'tkazish
└── api_client.py       — Backend API bilan aloqa
```

**Bot qanday ishlaydi:**
1. Foydalanuvchi `/start` yozadi
2. Bot telefon raqamini so'raydi (Telegram'dagi kontakt tugmasi orqali)
3. Raqam kelganda `POST /api/users/ensure` → user DBda yaratiladi
4. `POST /auth/request-code` → 6 raqamli OTP oladi → foydalanuvchiga yuboradi
5. Foydalanuvchi kodni web saytga kiritadi va kiradi

**Hamkorlik tokeni oqimi:**
- Foydalanuvchi `?start=partner_TOKEN` bilan kelsa → `/api/partners/accept` chaqiriladi

**Throttling:** `middlewares/throttling.py` — bir soniyada ko'p so'rov yuborsa sekinlashtiradi.

---

## Ma'lumotlar oqimi — To'liq rasmi

```
[Telegram Bot]
     |
     | X-API-KEY
     ↓
[Flask Backend] ←→ [PostgreSQL DB]
     |
     | Bearer Token
     ↓
[React Web App / Mini App]
     |
     | Recharts, React Router
     ↓
[Foydalanuvchi brauzeri]
```

### Kirish jarayoni (OTP):
```
Foydalanuvchi → Bot (/start)
Bot → Backend (POST /auth/request-code) [X-API-KEY]
Backend → Bot: OTP kodi
Bot → Foydalanuvchi: "Kod: 123456"
Foydalanuvchi → Web sayt: kod kiritadi
Web sayt → Backend (POST /auth/verify-code)
Backend → Web sayt: session_token
Web sayt → localStorage: token saqlaydi
```

### Dashboard yuklanish:
```
React App yuklanadi
→ DashboardContext.fetchDashboard()
→ GET /api/me/dashboard [Bearer token]
→ Backend: 5 parallel DB so'rov
→ JSON: {user, categories, types, seedlings, sales_summary}
→ Context state yangilanadi
→ Dashboard, Inventory, Settings sahifalari ko'rsatiladi
```

---

## Xavfsizlik choralari

| Chora | Qayerda | Nega |
|-------|---------|------|
| OTP hash (SHA-256) | `login_codes` jadvali | DB sizib chiqsa kod bilinmaydi |
| Session token hash | `sessions` jadvali | Xuddi shu sabab |
| `hmac.compare_digest` | `safe_equal()` | Timing attack'ga yo'l qo'ymaslik |
| HMAC-SHA256 | Telegram initData | Bot tokensiz imzolashning iloji yo'q |
| SQL `%s` placeholder | Barcha DB so'rovlar | SQL injection himoyasi |
| CORS whitelist | `app.py` | Boshqa domenlardan so'rov bloklanadi |
| Session limit (3) | `_insert_session()` | Bir foydalanuvchida cheksiz session bo'lmaydi |
| Ownership check | `sales.py` | Boshqa foydalanuvchi sortini sotib bo'lmaydi |

---

## Muhit o'zgaruvchilari (`.env` fayllari)

### `backend/.env`
```
DATABASE_URL=postgresql://user:pass@host/dbname
API_KEY=...              # Bot ↔ Backend kaliti
BOT_TOKEN=...            # Telegram bot tokeni
TG_BOT_USERNAME=...      # @BotNomi
IMGBB_API_KEY=...        # Rasmlar uchun
FLASK_ENV=production
```

### `client/.env`
```
VITE_API_BASE_URL=https://kochatim.uz  # yoki http://localhost:8000
```

### `miniApp/.env`
```
VITE_API_BASE_URL=https://kochatim.uz
```

### `bot/.env`
```
BOT_TOKEN=...
API_URL=https://kochatim.uz
API_KEY=...
ADMINS=...   # Admin Telegram ID lari
```

---

## Ishga tushirish

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:8000 --workers 4
```

### Client
```bash
cd client
npm install
npm run dev      # development
npm run build    # production build
```

### MiniApp
```bash
cd miniApp
npm install
npm run dev
```

### Bot
```bash
cd bot
pip install -r requirements.txt
python app.py
```

---

## Xulosa

**Ko'chatim** — ko'chat bog'bonlari uchun to'liq yechim:
- **Backend (Flask + PostgreSQL)** — ishonchli, tez, xavfsiz REST API
- **Web ilova (React + Vite)** — qulay boshqaruv paneli
- **Telegram Mini App** — tezkor kirish (Telegram ichida)
- **Telegram Bot** — ro'yxatdan o'tish, inventar va sotuv boshqaruvi

Barcha qismlar bitta API backend bilan ishlaydi. Autentifikatsiya OTP + session token asosida. Ma'lumotlar PostgreSQL da saqlanadi, rasmlar ImgBB'da.
