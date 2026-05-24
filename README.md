# Ko'chatim — Greenhouse Management System

Ko'chatim is a full-stack platform for managing greenhouse inventory, seedling sales, partners, and analytics. It consists of three tightly integrated components: a **React web client**, a **Flask REST API**, and a **Telegram bot**.

## Architecture

```mermaid
graph TD
    User((User))
    Browser[Web Browser / Client]
    TG[Telegram App]
    Bot[Telegram Bot]
    Backend[Backend API]
    DB[(PostgreSQL)]

    User -->|Opens| Browser
    User -->|Chats with| TG

    Browser -->|REST / Session token| Backend
    TG -->|Updates + deep-links| Bot
    Bot -->|REST / API key| Backend

    Backend -->|SQL| DB
```

---

## Components

### 1. Client (`/client`)

**Stack:** React 18, Vite, SCSS, Recharts, Lucide React

The primary user interface — responsive on both desktop and mobile, localized in Uzbek.

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home | Public landing page with gardener search |
| `/login` | Login | Sign in via OTP (SMS) or Telegram WebApp auto-login |
| `/dashboard` | Dashboard | Inventory overview, sales chart, and key metrics |
| `/inventory` | Inventory | Browse and manage seedling groups and varieties |
| `/sales` | Sales History | Full sales log with totals and filters |
| `/gardener/:u_id` | Gardener Profile | Public inventory view of another user |
| `/settings` | Settings | Profile info, partners, active sessions, and theme |

**Key features:**
- Automatic Telegram WebApp login via `TelegramHandler` — no manual sign-in needed when opened inside the bot
- Dark / Light theme toggle
- Partner system — generate an invite link, accept or reject incoming invites, remove partners
- Active session management — device name, city, IP address, current session highlight, remote logout
- Dashboard data cached for 60 seconds

---

### 2. Backend (`/backend`)

**Stack:** Python 3.11, Flask, Psycopg2 (connection pool), Gunicorn

The central API consumed by both the client and the bot. All routes are protected by either a **session token** (client) or an **API key** (bot).

#### Authentication — `/auth`

| Method | Endpoint | Caller | Description |
|--------|----------|--------|-------------|
| POST | `/auth/telegram-webapp` | Client, Bot | Login via Telegram WebApp `initData` |
| POST | `/auth/user-id-login` | Bot | Exchange Telegram user ID for a session token |
| POST | `/auth/request-code` | Client | Send an OTP code to the user's phone |
| POST | `/auth/verify-code` | Client | Verify the OTP code and create a session |

#### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/me` | Current user's profile |
| POST | `/api/users/ensure` | Create or update a user record (bot) |
| GET | `/api/users/:u_id` | Another user's public profile |
| GET | `/api/gardeners` | Search public gardener profiles |

#### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/me/dashboard` | Full dashboard data for the current user (60s cache) |
| GET | `/api/users/:u_id/dashboard` | Public dashboard for another user |

#### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET / POST | `/api/categories` | List or create seedling groups |
| PUT / DELETE | `/api/categories/:c_id` | Edit or delete a group |
| GET / POST | `/api/types` | List or create seedling varieties |
| PUT / DELETE | `/api/types/:t_id` | Edit or delete a variety |
| GET / POST | `/api/seedlings` | View or update seedling stock counts |

#### Sales

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sales` | Full sales history |
| POST | `/api/sales` | Record a new sale (bot) |

#### Partners

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/partners` | List current user's partners |
| GET | `/api/partners/invite-token` | Generate a one-time invite token (valid 7 days) |
| POST | `/api/partners/accept` | Accept an invite (bot) |
| POST | `/api/partners/decline` | Decline an invite (bot) |
| POST | `/api/partners/remove` | Remove a partner |
| GET | `/api/users/:u_id/partners` | List a user's partners (bot) |

#### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sessions` | List active sessions with device, city, and IP |
| DELETE | `/api/sessions/:session_id` | Revoke a specific session |

#### Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/img` | Attach an image to a variety by Telegram file ID (bot) |
| POST | `/api/img/upload` | Upload an image directly (client) |
| GET | `/api/img/:file_id` | Proxy a Telegram image to the browser |

---

### 3. Bot (`/bot`)

**Stack:** Python, Aiogram 2.x, Aiohttp

Handles user onboarding and day-to-day seedling operations via Telegram.

| Trigger | Description |
|---------|-------------|
| `/start` | Welcome flow — request phone if unregistered, or show main menu |
| `/start partner_TOKEN` | Show a partnership invite with accept / decline buttons |
| Contact share | Register the user, save profile photo, open main menu |
| Ko'rish | Browse seedling inventory |
| Qo'shish | Add a new group, variety, or seedling entry |
| Sotuv | Record a sale |
| Boshqaruv | Edit or delete existing groups and varieties |

**Partner invite flow:**
1. User A generates an invite link from the web client.
2. User B opens `/start partner_TOKEN` in the bot.
3. Bot presents Accept / Decline buttons.
4. On accept — both users become partners and each receives a confirmation message.
5. On decline — the token is discarded, no changes are made.

---

## Database

PostgreSQL with the following core tables:

| Table | Description |
|-------|-------------|
| `users` | Registered users — Telegram ID, phone, name, profile photo |
| `categories` | Seedling groups (e.g. fruit trees, flowers) |
| `types` | Seedling varieties within a group |
| `seedlings` | Stock counts per variety — small / medium / large |
| `img` | Images linked to varieties (Telegram file ID or URL) |
| `sales` | Sales records — quantity, price, timestamp |
| `sessions` | Active login sessions — device name, city, IP, expiry |
| `partners` | Bidirectional partner links between users |
| `partner_invites` | One-time invite tokens — expire after 7 days or first use |

---

## Setup

**Requirements:** Python 3.11+, Node.js 18+, PostgreSQL

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in values
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/kochatim
BOT_TOKEN=...
API_KEY=...
SESSION_TTL_SECONDS=2592000
FLASK_ENV=production
```

### Bot

```bash
cd bot
pip install -r requirements.txt
cp .env.example .env
python app.py
```

```env
BOT_TOKEN=...
API_URL=http://127.0.0.1:8000
API_KEY=...
ADMINS=123456789
WEB_URL=https://kochatim.uz
TG_BOT_USERNAME=kochatim_bot
```

### Client

```bash
cd client
npm install
cp .env.example .env
npm run dev      # development
npm run build    # production build
```




---

## Authentication

Two sign-in methods are supported:

- **OTP** — the user enters their phone number, receives a code via Telegram message, and a session is created on successful verification.
- **Telegram WebApp** — when the client is opened through the bot, `initData` is verified server-side automatically and a session is issued without any manual step.

Sessions are stored in the `sessions` table. A maximum of **3 active sessions** are kept per user — the oldest is removed when a fourth is created.
