# Kochatim Agent Instructions

These instructions govern any AI coding agent (Claude Code, Cursor, …)
working in this repository. Read them before making changes, and keep
this file updated when the architecture or the rules change.

## Project

Kochatim is a seedling nursery management platform for Uzbek gardeners
(*bog'bonlar*). A gardener keeps a catalogue of plant groups
(`categories`) and varieties (`types`), tracks stock in three quality
grades, records sales, and shares inventory with partners.

Stack:

- Flask 3 (no ORM — hand-written SQL through `psycopg2`)
- PostgreSQL 16
- Redis 7 (cache, pub/sub, counters, startup lock)
- aiogram 2.x (Telegram bot)
- React 19 + Vite (web client)
- Docker Compose

Services, each its own directory and image:

| Directory | What it is | Port |
|---|---|---|
| `backend/` | Flask REST API — the only service that touches Postgres | 8000 |
| `bot/` | aiogram Telegram bot; reaches the backend over HTTP | — |
| `admin/` | Flask + Socket.IO monitoring panel; reads Redis only | 9000 |
| `client/` | React/Vite dashboard served by nginx | 80 |

Run the whole stack with `docker compose up --build`. See
`docs/setup.md`.

## Architecture Rules

- **The backend owns the database.** `bot/` and `admin/` must never
  open a Postgres connection. The bot goes through the REST API; the
  admin panel reads Redis keys the backend writes.
- **No raw SQL outside `backend/`.** Inside the backend, every query
  goes through `db.py` (`execute`, `execute_returning`, `fetch_one`,
  `fetch_all`) so the retry-once-on-dropped-connection logic applies
  everywhere.
- **Always parameterise SQL.** `%s` placeholders with a params tuple,
  never f-strings or `+` with user input. The one place a query is
  assembled dynamically (`api/users.py:search_gardeners`,
  `api/dashboard.py:partner_dashboards`) still passes values as
  params — only the number of placeholders is built, never a value.
- **Nothing answers without a key.** `middleware/client_gate.py` runs
  before every route and returns a bare 401 unless the request carries
  the bot key (`X-API-KEY`) or the web client key (`X-Client-Key`).
  `/health` and CORS preflights are the only exceptions. Do not add a
  route that bypasses it.
- **Extend, don't replace.** The existing structure (`api/`, `auth/`,
  `middleware/`, `utils/`) is the shape to work within.
- **Schema changes go in `backend/db_init.py`.** There is no migration
  tool. `init_db()` is idempotent (`CREATE TABLE IF NOT EXISTS`,
  `ADD COLUMN IF NOT EXISTS`) and runs on every backend start behind a
  Redis lock. A new column must be added both to the `CREATE TABLE`
  and as an `ALTER TABLE ... IF NOT EXISTS`, or existing deployments
  will not pick it up.

## Backend Rules

- Every endpoint returns through `utils/errors.py` — `ok(data)` or
  `fail(message, status, code=...)`. Never return a bare dict or let an
  exception escape to Flask's HTML error page. Clients parse
  `{ok, data}` / `{ok, error}` and nothing else.
- Validate input explicitly. `isinstance(u_id, int)` is the house
  style; there is no Pydantic here. A missing or wrong-typed field gets
  a 400 with a `code`, not a 500.
- `g.u_id` is set by `require_session` and is the only trustworthy
  identity on a session route. Never read `u_id` from the request body
  on a session-authenticated endpoint — that is an IDOR.
- **The server decides the caller's IP and browser; the caller does
  not.** `utils/device.get_client_ip` believes only the TCP peer and,
  from our own nginx, `X-Real-IP`. It never reads `X-Forwarded-For`.
  Do not add a function that takes `ip` or `user_agent` as a parameter
  or reads them from a body or query string.
- Never put `str(e)` in a response. It can contain SQL, a DSN, or a URL
  with the bot token in it. Log it; return a fixed message.
- Stock and money changes are one statement or one `db.transaction()`.
  Read-check-write across separate calls is a race.
- Cache writes must be paired with invalidation. Mutating categories,
  types, seedlings or sales calls `invalidate_dashboard_cache(u_id)`.
  Mutating partners calls `_invalidate_partners(u_id)` for **both**
  sides of the relationship.
- External HTTP calls always pass `timeout=`. `utils/device.py`,
  `utils/images_v2.py` and `utils/telegram_notify.py` sit on the login
  and write paths; a hanging call there stalls a request.

## Access control: one gate, two credentials

Three layers, outermost first. A request must pass all that apply.

### 1. The client gate — `middleware/client_gate.py`
Every request carries one of two keys:

| Header | Config | Who | Sets |
|---|---|---|---|
| `X-API-KEY` | `API_KEY` | the bot (secret) | `g.client = "bot"` |
| `X-Client-Key` | `WEB_CLIENT_KEY` | the web client | `g.client = "web"` |

**The web key is not a secret** — it ships in the browser bundle
(`VITE_CLIENT_KEY`). It keeps scanners and `curl` out; it protects no
user's data on its own. Never treat holding it as proof of anything.

The two stay apart on purpose. `@require_api_key` accepts the bot key
only; `@require_session` accepts `g.client == "web"` only. If the web
key were accepted on a bot route it would be a master key, because bot
routes take `u_id` from the caller.

`test/integration/test_client_gate.py` walks every registered route. A
new route with neither decorator must be added to its `PUBLIC_ENDPOINTS`
with a reason, or the test fails.

### 2. `@require_api_key` — the bot
`X-API-KEY`, compared in constant time against `Config.API_KEY`. A
**service** credential: it identifies the bot process, not a person.
Routes behind it take `u_id` as a parameter, so the caller chooses whose
data it touches. Never expose such a route to the browser.

### 3. `@require_session` — the web client
`Authorization: Bearer <token>` **and** `X-Session-Proof`. The token is
hashed (`sha256_hex`) and looked up in `sessions`; the cache entry
(120 s) holds the session's device key. Sets `g.u_id` and `g.token_hash`.
A **user** credential — scope every query by `g.u_id`.

The token is bound to a key pair the browser made at login
(`extractable=false`, so neither page script nor a copy of localStorage
can read the private half). Every request carries a fresh ECDSA signature
over method + path + query + nonce + the token's hash
(`utils/device_proof.py`, `client/src/api/deviceKey.js`). A token pasted
into another browser has no key to sign with and gets a 401. Proofs are
single-use (Redis nonce) and valid for `PROOF_MAX_SKEW_SECONDS`.

A session is also tied to the browser + OS family it was created from;
a different one ends it. Sessions with no device key are never honoured.

**Logging in** always needs the browser's public key (`device_key`) and
ends in `auth/session_service.create_session(u_id, device_key)`:
`POST /auth/verify-code` (OTP the bot delivered) or
`POST /auth/telegram-webapp` (HMAC-verified initData, at most
`INITDATA_MAX_AGE_SECONDS` old). **Knowing a `u_id` is not enough to get a
session** — there is no route that mints one from a user id.

`get_viewer()` is the soft version for public routes that show more to a
signed-in viewer: it returns the `u_id` or `None` and never rejects.

A route with no decorator is public *to holders of a key*. There are
seven: `/health`, the two login endpoints, the gardener directory and
profile (names only unless the viewer is a partner), the image proxy, and
the public category list.

## Known Security Issues

Fixed (see `docs/security.md` for what changed and why):
the `u_id`-only login, token portability, the open API, spoofable client
IP, `str(e)` leaks, public phone numbers, the admin panel's missing auth
and stored XSS, OTP guessing, stale initData, the stock race, the
non-transactional sale, and three smaller logic bugs.

Still open, and in a **public** repository — do not write exploit code
for them here:

1. **Nothing prunes `sessions` or `login_codes`.** Expired rows pile up.
2. **`price` is `REAL`** (a float) in `sales` and `seedlings_logs`.
3. **The web client key is public by design.** Rotate it by changing
   `WEB_CLIENT_KEY` and `VITE_CLIENT_KEY` together and redeploying both.
4. **Telegram/ImgBB URLs are logged with secrets** in a few `print`
   calls in `utils/images_v2.py`. Not returned to clients; still in logs.

Local audit notes (`hacking_map.md`, `hacking_map_advanced.md`) are
gitignored for that reason and must stay so.

## Testing

Every new endpoint and every new util function ships with three tests:

1. **Success** — a valid, representative call returns what it claims.
2. **Invalid input** — missing field, wrong type, out-of-range value.
   Asserts a 400/404 with a `code`, never an unhandled exception.
3. **Dependency failure** — Postgres, Redis or an external HTTP call
   raises. Asserts a clean error rather than a stack trace, and for
   anything on the request path, that the user's request still
   succeeds where the code is written to swallow the failure.

Run everything:

```bash
./scripts/test.sh              # all four suites locally
./scripts/test.sh --docker     # inside the service base images
./scripts/test.sh backend      # one suite
```

Each service has its own pytest root — `test/` (backend),
`admin/tests/`, `bot/tests/` — because `bot/utils/` and
`backend/utils/` are different packages with the same name. The client
uses Vitest (`cd client && npm test`).

**Read `skills/testing/SKILL.md` before writing a test here.** This
codebase has a dozen import-time and threading traps that will cost
hours otherwise: config is evaluated at import, `app.py` builds the app
and starts a thread at module level, CORS is registered outside the
factory, a star-import shadows a module name, and aiogram will not
install on Python 3.13.

## Git

An agent must **not** run `git commit`, `git push`, or open a pull
request unless asked for it in that message. Finishing a task is not
permission. Stop at a clean working tree, report what changed, and let
the owner decide.

Branches: work on `feat/*` or `fix/*`, open a PR against `main`.

This project's history credits the agent — commits carry a
`Co-Authored-By:` trailer for the model that wrote them. Keep doing
that; it is the existing convention here.

## Secrets

Never commit:

- `API_KEY` (the bot ↔ backend shared secret)
- `INVITE_SECRET`, `ADMIN_PASSWORD`
- `BOT_TOKEN`
- database or Redis passwords
- `IMGBB_API_KEY`

`WEB_CLIENT_KEY` / `VITE_CLIENT_KEY` are not secrets (the browser ships
them) but must still differ from `API_KEY`; a production backend refuses
to start otherwise (`Config.validate`).

`.env` files are gitignored and must stay that way. Every service has a
committed `.env.example` with placeholder values — when you add a
setting, add it there too.

`hacking_map.md` and `hacking_map_advanced.md` are gitignored: they are
working exploit guides, and this repository is public.

## Documentation Map

| File | Covers |
|---|---|
| `docs/architecture.md` | Services, request flows, what Redis is used for |
| `docs/setup.md` | Running it locally |
| `docs/api.md` | Every route, its auth, and its response shape |
| `docs/database.md` | Tables, indexes, and the no-migrations approach |
| `docs/backend.md` | Flask app structure, the db layer, caching |
| `docs/bot.md` | aiogram handlers, FSM states, the API client |
| `docs/admin.md` | The monitoring panel and its Redis contract |
| `docs/frontend.md` | React structure, `apiFetch`, the dashboard transform |
| `docs/testing.md` | Suite layout, what is covered, how to run it |
| `docs/deployment.md` | Docker Compose, single-server layout, nginx |
| `docs/security.md` | The known issues, with severity and fixes |

| Skill | Load it when |
|---|---|
| `skills/backend/SKILL.md` | Writing or editing a Flask endpoint or util |
| `skills/bot/SKILL.md` | Writing an aiogram handler |
| `skills/frontend/SKILL.md` | Writing React components or API calls |
| `skills/testing/SKILL.md` | Writing any test — read this first |
| `skills/deployment/SKILL.md` | Touching Docker, Compose, or nginx |
