---
name: kochatim-backend
description: Enforces Kochatim's backend rules. Use whenever writing or editing a Flask endpoint, a util, or anything under backend/ — even when the request is just "add an endpoint" or "fix this query" without mentioning architecture. Covers the two authentication paths and how to choose between them, the ok()/fail() response contract, scoping queries by g.u_id to avoid IDOR, cache invalidation, the db.py retry semantics, and the import-time behaviour of config.py and app.py.
---

# Kochatim Backend Rules

Flask 3, no ORM, hand-written parameterised SQL. Apply these any time
you touch `backend/`, not only when asked about architecture.

## Choose the authentication path deliberately

Every protected route gets exactly one decorator, and which one is a
design decision.

### `@require_api_key` — the bot
`X-API-KEY`, compared against `Config.API_KEY`. This is a **service**
credential: it identifies the bot process, not a person. Routes behind
it take `u_id` as a parameter, so the caller chooses whose data it
touches.

Never expose such a route to the browser, and never add one that the
web client needs — that would mean shipping the shared secret to the
front end.

### `@require_session` — the web client
`Authorization: Bearer <token>`. Sets `g.u_id` and `g.token_hash`.

**`g.u_id` is the only trustworthy identity here.** Reading `u_id` from
the request body on a session route is an IDOR — the caller would pick
whose data to read:

```python
# WRONG on a session route
u_id = request.get_json().get("u_id")

# RIGHT
u_id = int(g.u_id)
```

Every query on a session route must be scoped by it:

```python
fetch_all("SELECT c_id, c_name FROM categories WHERE u_id=%s", (u_id,))
```

There are no foreign keys in this schema, so that `WHERE u_id = %s` is
the *only* thing keeping users' data apart. A query that forgets it
reads across accounts.

### No decorator = public
Eight routes have no auth decorator. Three are the login endpoints and
have to be public; of the other five, three are deliberate (`/health`,
the Telegram image proxy, the public category list) and two already
leak phone numbers (`docs/security.md`, issue 4).

**Do not add another without a reason you can write down**, and if you
do, check its `SELECT` list for PII — `u_phone` especially.

`GET /api/v1/public/categories` is the model: it selects only
`c_id AS id, c_name AS name`, with no `u_id`, so the open list cannot
be scraped for Telegram IDs.

## Always return through `ok()` / `fail()`

```python
from utils.errors import ok, fail

return ok({"created": True, "c_id": c_id})
return fail("c_name required", 400)
return fail("Guruh topilmadi", 404, code="NOT_FOUND")
```

Clients parse `{ok, data}` / `{ok, error}` and nothing else — both the
bot's two HTTP clients and the web client's `apiFetch` raise on
`ok: false` **even with HTTP 200**. A bare dict or an escaped exception
breaks all three.

Give failures a `code`. Clients branch on it; messages are in Uzbek and
get reworded. Existing codes: `UNAUTHORIZED`, `SERVER_MISCONFIG`,
`NOT_FOUND`, `ALREADY_EXISTS`, `INSUFFICIENT_STOCK`, `INVALID_CODE`,
`CODE_NOT_FOUND`, `CODE_USED`, `CODE_EXPIRED`, `INVALID_INITDATA`,
`INVALID_TOKEN`, `INVITE_USED`, `INVITE_EXPIRED`, `SELF`.

## Validate input explicitly

There is no Pydantic here. The house style:

```python
data = request.get_json(silent=True) or {}
u_id = data.get("u_id")
if not isinstance(u_id, int):
    return fail("u_id(int) required", 400)
```

`get_json(silent=True) or {}` matters — without it a malformed body
raises and becomes a 500 rather than a 400.

A missing or wrong-typed field is a **400 with a code**, never a 500.
Use `request.args.get("u_id", type=int)` for query params, which
returns `None` rather than raising on garbage.

## Every query goes through `db.py`

`execute`, `execute_returning`, `fetch_one`, `fetch_all`. Never take a
connection from the pool directly in a handler — these four carry the
retry-once-on-dropped-connection logic, and code that bypasses them
loses it.

```python
row = fetch_one("SELECT c_id FROM categories WHERE c_id=%s AND u_id=%s",
                (c_id, u_id))
```

### Parameterise everything

`%s` placeholders with a params tuple. Never f-strings, never `+`, never
`%` formatting with user input. When the *number* of placeholders must
vary, build only the placeholders:

```python
ph = ",".join(["%s"] * len(partner_ids))
fetch_all(f"SELECT ... WHERE u_id IN ({ph})", tuple(partner_ids))
```

That is the one acceptable form of dynamic SQL here: the values still
travel as params.

### Writes that need a reading first

`execute_returning` exists so an insert can hand back the new row in
one round trip:

```python
row = execute_returning(
    "INSERT INTO categories (u_id, c_name) VALUES (%s, %s) RETURNING c_id, c_name",
    (u_id, c_name),
)
if not row:
    return fail("Guruhni saqlashda xatolik yuz berdi", 500)
```

Prefer it over `execute` followed by `fetch_one`, which races.

### There are no transactions

Every `db.py` function commits on its own. Two statements that must
succeed together currently cannot be — `POST /api/sales` has exactly
this bug (`security.md`, issue 5). If you need atomicity, add a helper
to `db.py` that yields a cursor and commits once; do not open a
connection by hand in a handler.

## Invalidate the cache you invalidate

A write without its invalidation leaves the dashboard stale for up to
60 seconds, which users report as "my change didn't save".

| You wrote to | Call |
|---|---|
| categories, types, seedlings, sales | `invalidate_dashboard_cache(u_id)` |
| partners | `_invalidate_partners(u_id)` for **both** users |
| sessions | `invalidate_session_cache(token_hash)`, plus `sessions_<u_id>` and `settings_<u_id>` |

Partnerships are symmetric — two rows in `partners` — so both sides'
caches are stale after a change.

When adding a cached read, add its key to the table in
`docs/architecture.md`.

## Pass `timeout=` to every outbound call

`get_city` (ip-api.com), the ImgBB upload, and the Telegram calls all
sit on request paths — login and writes. A call without a timeout
stalls a gunicorn worker indefinitely.

Follow the surrounding pattern of swallowing the failure and degrading:
`get_city` returns `""`, `send_message` returns `None`,
`upload_to_imgbb` returns `None`. A city lookup failing must not fail
a login.

## Two import-time behaviours to know

**`config.py` is evaluated once, at import.** `Config`'s attributes are
class-body assignments, so `os.getenv` runs on first import and later
changes to `os.environ` have no effect. Missing secrets become empty
strings rather than raising — the guard is downstream
(`require_api_key` returns `SERVER_MISCONFIG` on an empty key).

**`app.py` builds the app and starts a thread at import.**
`app = create_app()` runs at module level, and `system_monitor` starts
as a daemon thread. More importantly:

> The CORS handlers and `_record_endpoint_stats` are registered with
> `@app.before_request` / `@app.after_request` on the **module-level**
> `app`, not inside `create_app()`. An app built by calling
> `create_app()` has neither.

Gunicorn serves `app:app`, so production gets the configured instance.
If you add another cross-cutting hook, put it with the others.

## Schema changes: edit two places

There is no migration tool. `db_init.py:init_db()` runs on every
backend start. Adding a column means **both**:

```python
# 1. the CREATE TABLE body, for fresh installs
execute("""CREATE TABLE IF NOT EXISTS users(... u_photo TEXT ...);""")

# 2. an idempotent ALTER, for existing databases
execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS u_photo TEXT;")
```

Editing only the `CREATE TABLE` silently does nothing on a deployed
database. Every statement must stay idempotent: four gunicorn workers
race for a Redis lock and the losers skip, but if Redis is down all
four run.

## Time

All columns are `TIMESTAMP` without time zone. Generate UTC and strip
the offset before writing:

```python
expires_at = naive_utc(utc_in_seconds(Config.SESSION_TTL_SECONDS))
```

Compare with `NOW() AT TIME ZONE 'utc'` in SQL, never bare `NOW()`.
Writing a tz-aware datetime produces an offset bug that only shows up
away from UTC. (`auth/user_id_login.py` currently writes a tz-aware
value where the other two auth paths write naive — don't copy it.)

## Never commit secrets

`API_KEY`, `BOT_TOKEN`, database and Redis passwords, `IMGBB_API_KEY`.
`.env` files are gitignored. When you add a setting, add it to that
service's `.env.example` with a placeholder, and document it in
`docs/setup.md`.

## Before you finish

Every new endpoint ships with three tests — success, invalid input, and
dependency failure — plus a 401 check if it is authenticated. **Read
`skills/testing/SKILL.md` first**; this codebase has import-time and
threading traps that will otherwise cost you hours.

Update `docs/api.md` with the route, its auth, and its response shape.
