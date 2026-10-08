# Architecture and Data Flow

Four services, each in its own directory and Docker image. This doc
describes what each one actually does and how data moves between them,
traced from the code rather than assumed from the stack list.

## Services

| Service | Role | Talks to |
|---|---|---|
| `backend` | Flask REST API. Owns the database: schema creation, all reads and writes. Serves both the bot (API-key auth) and the web client (session auth). Publishes metrics and request events to Redis. | Postgres, Redis, Telegram API, ImgBB, ip-api.com |
| `bot` | aiogram 2.x Telegram bot. The gardener's primary interface: add groups and varieties, record stock and sales, accept partner invites, request a web login code. Holds no database access. | `backend` (HTTP), Telegram API |
| `admin` | Flask + Socket.IO monitoring panel. Streams CPU/RAM and a live request feed over WebSocket, and shows daily/weekly request counts. Reads Redis only — it never queries Postgres. | Redis |
| `client` | React 19 + Vite dashboard, built to static files and served by nginx. | `backend` (HTTP) |

Everything runs on one host on one Docker network (`kochatim`). There
is no load balancer and no service mesh; `docker-compose.yml` is the
whole topology.

## Request flows

### The gardener in Telegram

```
gardener ──► bot (aiogram) ──X-API-KEY──► backend ──► Postgres
```

The bot never holds a user session. It authenticates to the backend
with a single shared `API_KEY` and passes the gardener's Telegram ID as
`u_id` in the body or path. That makes the API key a **service**
credential: whoever holds it can act for any user.

### The gardener on the web

```
gardener ──► client (nginx) ──Bearer token──► backend ──► Postgres
                                                  │
                                                  └──► Redis (session + dashboard cache)
```

Three ways to get a session token:

1. **OTP** — the bot calls `POST /auth/request-code` (API key), gets a
   6-digit code, shows it to the gardener, who types it into the web
   form. `POST /auth/verify-code` exchanges it for a session token.
   The code is stored as a SHA-256 hash, single-use, 120s TTL.
2. **Telegram Mini App** — `POST /auth/telegram-webapp` verifies the
   `initData` HMAC against `BOT_TOKEN` and issues a token. This is the
   cryptographically sound path.
3. **`POST /auth/user-id-login`** — issues a token for any existing
   `u_id` with no proof whatsoever. This is an authentication bypass;
   see `security.md`.

A gardener keeps at most 3 concurrent sessions; inserting a fourth
deletes the oldest (`_MAX_SESSIONS` in each auth module).

### Monitoring

```
backend ──publish──► Redis "server_metrics" ──► admin ──Socket.IO──► browser
backend ──publish──► Redis "live_requests"  ──► admin ──Socket.IO──► browser
backend ──incr────► Redis "req_count:<date>" ──► admin GET /api/stats
backend ──zincrby─► Redis "endpoint_stats"   ──► admin GET /api/stats
```

A daemon thread in `backend/app.py` (`system_monitor`) samples CPU and
RAM every 2 seconds and publishes them. If either exceeds 90% it sends
a Telegram message to every ID in `ADMINS`, rate-limited to one alert
per 5 minutes.

An `after_request` hook (`_record_endpoint_stats`) counts every
`/api/*` and `/auth/*` request. The whole hook is wrapped in
`try/except: pass` — monitoring must never break a user's request.

## What Redis is used for

Five distinct jobs on one instance. Worth knowing, because they have
very different consequences when Redis is unavailable.

| Purpose | Keys | If Redis is down |
|---|---|---|
| Session lookup cache | `session_<token_hash>`, 120s | Falls through to Postgres. Slower, still correct. |
| Response cache | `dashboard_<u_id>` (60s), `partners_<u_id>` (300s), `settings_<u_id>` (120s), `sessions_<u_id>` (120s), `invite_token_<u_id>` (1800s), `partner_dashboards_<u_id>` (300s) | Cache miss every time. Slower, still correct. |
| Request counters | `req_count:<YYYY-MM-DD>` (8d TTL), `endpoint_stats` (sorted set) | Counts stop; admin panel shows zeroes. |
| Live feed | pub/sub channels `server_metrics`, `live_requests` | Panel goes quiet. |
| Startup lock | `global_db_init_lock` (15s, `NX`) | `init_db()` runs unguarded on every worker. |

Every cache function in `utils/cache.py` catches its own exceptions and
degrades to a miss, so a Redis outage slows the app but does not break
it. The one exception is `db_init`, which logs and continues without
the lock.

## Schema creation has no migration tool

`backend/db_init.py:init_db()` runs on **every backend start**. It
creates tables with `CREATE TABLE IF NOT EXISTS`, adds columns with
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, and creates triggers and
indexes idempotently.

Gunicorn runs 4 workers, so four processes would race. A Redis lock
(`SET global_db_init_lock NX EX 15`) lets one win; the others sleep 2
seconds and skip. If Redis is unavailable the lock is skipped and all
four run — which is safe only because every statement is idempotent.

The consequence for a change: **adding a column means editing two
places** — the `CREATE TABLE` body for fresh installs, and an
`ALTER TABLE ... IF NOT EXISTS` for existing ones. Editing only the
`CREATE TABLE` silently does nothing on a deployed database.

## Images take two different paths

Variety photos arrive either from Telegram (a `file_id`) or from a
browser upload (raw bytes), and the two are stored differently.

```
bot:     file_id ──► backend/utils/images_v2.py ──getFile──► Telegram
                                                ──upload──► ImgBB ──► https URL in img.i_url
browser: bytes   ──► POST /api/img/upload ──► ImgBB ──► https URL returned to client
```

`process_image_input()` decides: a value already starting with
`http://` or `https://` is stored as-is; anything else is treated as a
Telegram `file_id` and converted. If conversion fails it stores the
original value, which is why `img.i_url` can hold a bare `file_id`.

That is what `GET /api/img/<file_id>` exists for — a public proxy that
resolves a `file_id` through Telegram and streams the bytes back, so
old rows still render. The client's `toWebImgUrl()` routes any
non-URL value through it.

## Concurrency

Three places run work off the request thread. All three are worth
knowing about because they change how the code can be tested and what
happens when they fail.

- **`backend/app.py`** — `system_monitor` daemon thread, started at
  module import. Runs forever.
- **`backend/api/dashboard.py`** — a module-level `ThreadPoolExecutor`
  (`max(2, DB_POOL_MAX // 2)` workers) runs the dashboard's five
  queries concurrently. Sized against the DB pool deliberately: more
  workers than connections would just queue on the pool.
- **`backend/auth/user_id_login.py`** — a 100-worker
  `ThreadPoolExecutor` writes the session row *after* the response is
  sent, so the login call does not wait for the ip-api.com city
  lookup. Failures are logged and swallowed, which means a login can
  return a token whose session row was never written.

## Client structure

The React app reads one endpoint for most of its state —
`GET /api/me/dashboard` returns user, categories, types, seedlings and
a sales summary in a single response — and reshapes it client-side.

```
dashboard response ──► buildGroupsFromDashboard() ──► [{ groupName, sorts, totalValue, groupImages }]
```

`buildGroupsFromDashboard` (`client/src/utils/buildGroups.js`) joins the
three flat lists into the nested shape the UI renders. Its one
non-obvious rule: a variety with no `seedlings` row still appears, with
zero counts — otherwise a newly added variety would vanish from the
dashboard until stock was entered.
