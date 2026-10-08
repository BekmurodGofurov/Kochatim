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
- Cache writes must be paired with invalidation. Mutating categories,
  types, seedlings or sales calls `invalidate_dashboard_cache(u_id)`.
  Mutating partners calls `_invalidate_partners(u_id)` for **both**
  sides of the relationship.
- External HTTP calls always pass `timeout=`. `utils/device.py`,
  `utils/images_v2.py` and `utils/telegram_notify.py` sit on the login
  and write paths; a hanging call there stalls a request.

## Two Authentication Paths

Every protected route uses exactly one of these. Which one is a design
decision, not a detail — pick deliberately.

### `@require_api_key` — the bot
`X-API-KEY` header, compared against `Config.API_KEY`. This is a
**service** credential: it identifies the bot process, not a person.
Routes behind it take `u_id` as a parameter, so the caller chooses
whose data it touches. Never expose such a route to the browser.

### `@require_session` — the web client
`Authorization: Bearer <token>`. The token is hashed
(`sha256_hex`) and looked up in `sessions`; the result is cached in
Redis for 120s. Sets `g.u_id` and `g.token_hash`. This is a **user**
credential — scope every query by `g.u_id`.

A route with neither decorator is public. There are eight. Three are
the login endpoints themselves and have to be
(`/auth/verify-code`, `/auth/telegram-webapp`, `/auth/user-id-login` —
though the last one should not exist at all). Of the remaining five,
three are deliberate (`/health`, the Telegram image proxy, the public
category list) and two leak phone numbers — see `docs/security.md`
before adding a ninth.

## Known Security Issues

These are real, unfixed, and in a **public** repository. Do not treat
them as examples to follow, and do not add code that depends on them.

1. **`POST /auth/user-id-login` is an authentication bypass.** It
   issues a valid session token for any `u_id` that exists, with no
   password, OTP or signature. A Telegram user ID is not a secret.
2. **The admin panel has no authentication.** Anything that can reach
   port 9000 reads the traffic stats.
3. **`@app.errorhandler(Exception)` returns `str(e)`** to the client in
   `error.extra`, which can include SQL and connection strings.
4. **`GET /api/gardeners` and `GET /api/users/<u_id>/dashboard`** are
   public and return `u_phone`.

`docs/security.md` has the detail and the fix for each. Do not write
the exploit for any of these into the repo — the local audit notes
(`hacking_map.md`) are gitignored for that reason, and must stay so.

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
- `BOT_TOKEN`
- database or Redis passwords
- `IMGBB_API_KEY`

`.env` files are gitignored and must stay that way. Every service has a
committed `.env.example` with placeholder values — when you add a
setting, add it there too.

`hacking_map.md` is gitignored: it is a working exploit guide for the
issues above, and this repository is public.

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
