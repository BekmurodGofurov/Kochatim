# Backend

Flask 3, no ORM, hand-written SQL. Served by gunicorn with 4 workers
in production (`app:app`), or Flask's dev server when `app.py` is run
directly with `FLASK_ENV != production`.

## Layout

```
backend/
  app.py            Flask app, CORS, error handlers, monitor thread
  config.py         Config — reads env at import time
  db.py             Query helpers with retry-once semantics
  extensions.py     psycopg2 ThreadedConnectionPool
  db_init.py        Schema creation, runs on every start
  auth/             Login routes (blueprint: /auth/*)
  api/              Everything else (blueprint: /api/*)
  middleware/       require_api_key, require_session
  utils/            Pure helpers — see below
```

## `app.py` — three things happen at import

This matters for testing and for anything that imports the module.

1. **`app = create_app()` at module level.** Calling `create_app()`
   opens the Postgres pool (`init_pool()`) and creates the schema
   (`init_db()`). Importing `app.py` therefore needs a live database
   unless those are patched.
2. **`system_monitor` starts as a daemon thread.** It samples CPU and
   RAM every 2 seconds forever, publishes to Redis, and alerts
   `ADMINS` over Telegram above 90% (at most one alert per 5 minutes).
3. **CORS and request stats are registered *after* `create_app()`**,
   with `@app.before_request` / `@app.after_request` on the
   module-level `app` object.

Point 3 has a consequence worth stating plainly: **an app returned by
`create_app()` has no CORS handling and no request stats.** Only the
module-level singleton does. Gunicorn serves `app:app`, so production
is fine — but any code that builds its own app via the factory gets a
differently-behaving application. The test suite uses the module-level
instance for exactly this reason.

If you add another cross-cutting hook, put it with the others and be
aware of this split. Moving all of them inside `create_app()` would be
an improvement, but it is a behaviour change — the factory would start
returning a different app than it does today.

## `config.py` — evaluated once, at import

`Config`'s attributes are class-body assignments, so every `os.getenv`
runs when the module is first imported. Changing `os.environ` later has
no effect.

```python
class Config:
    API_KEY = os.getenv("API_KEY", "").strip()
    ALLOWED_ORIGINS: set = set(...)
```

Missing secrets become empty strings rather than raising. The guard is
downstream: `require_api_key` returns `500 SERVER_MISCONFIG` when
`API_KEY` is empty, and `parse_partner_invite_token` fails closed. A
missing `PORT` or `DB_POOL_MAX` *does* raise, because `int()` fails.

`ALLOWED_ORIGINS` is a `set` of exact origins. Empty means reject
everything — there is no wildcard fallback.

## `db.py` — all four helpers, and why they retry

| Function | Commits | Returns |
|---|---|---|
| `execute(q, params)` | yes | `None` |
| `execute_returning(q, params)` | yes | `dict` or `None` |
| `fetch_one(q, params)` | no | `dict` or `None` |
| `fetch_all(q, params)` | no | `list[dict]` |

Every query in the backend goes through these. Each retries **once**
when the connection was dropped underneath it —
`psycopg2.OperationalError`, `InterfaceError`, or one of the message
patterns in `_is_retryable_db_error` ("server closed the connection
unexpectedly", "SSL connection has been closed unexpectedly",
"connection already closed", "terminating connection").

The important part is how the dead connection is disposed of:

```python
def _discard_conn(conn):
    put_conn(conn, close=True)   # NOT conn.close()
```

The connection came from the pool, so `conn.close()` alone would leave
the pool holding a closed handle and hand it to the next request.
`putconn(conn, close=True)` tells the pool to discard it.

Errors that are not transient — `ProgrammingError` (bad SQL),
`IntegrityError` (constraint violation) — raise immediately. Retrying a
syntax error accomplishes nothing.

Rows come back as plain dicts built from `cur.description`, which is
why handlers index with `row["u_id"]` rather than a tuple position.

## `extensions.py` — the pool

A single module-level `ThreadedConnectionPool`. `init_pool()` is
idempotent (returns early if `_pool` is not `None`), which matters
because `create_app()` can be called more than once.

```
real connection ceiling = gunicorn workers × DB_POOL_MAX
```

With the default `DB_POOL_MAX=100` and 4 workers that is 400, against
Postgres's default `max_connections` of 100. Set it to 20 or lower.
See `security.md`.

## Middleware

### `require_api_key`
Compares the `X-API-KEY` header against `Config.API_KEY`. Returns
`500 SERVER_MISCONFIG` if the server has no key configured, and
`401 UNAUTHORIZED` otherwise.

The comparison is `!=`, not `compare_digest`. A theoretical timing
side-channel; low practical risk over a network, but
`hmac.compare_digest` would cost nothing.

### `require_session`
Reads `Authorization: Bearer <token>`, hashes it with `sha256_hex`,
and resolves it to a `u_id`:

1. Redis `session_<token_hash>` — 120s TTL.
2. On a miss, Postgres, filtered by `expires_at > NOW() AT TIME ZONE
   'utc'`, then cached.

Sets `g.u_id` and `g.token_hash`. **`g.u_id` is the only trustworthy
identity on a session route** — never take `u_id` from the request body
there.

`invalidate_session_cache(token_hash)` makes logout immediate instead
of waiting out the TTL; `DELETE /api/sessions/<id>` calls it.

## `utils/`

| Module | Contents |
|---|---|
| `errors.py` | `ok(data, status)` / `fail(message, status, code, extra)` — the only two response shapes. |
| `security.py` | Token generation (`secrets`), `sha256_hex`, `safe_equal` (constant-time), Telegram `initData` HMAC verification, `parse_telegram_user`. |
| `time.py` | `utcnow()`, `utc_in_seconds()`, `naive_utc()`. |
| `cache.py` | Redis-backed cache. Every function swallows its own exceptions and degrades to a miss. |
| `device.py` | User-Agent parsing, `get_client_ip` (X-Forwarded-For aware), `get_city` via ip-api.com. |
| `images_v2.py` | ImgBB upload, Telegram `file_id` → URL, `process_image_input`. |
| `telegram_images.py` | A second `file_id` resolver with a module-level cache. Overlaps `images_v2` — kept because the proxy route uses a different code path. |
| `telegram_notify.py` | `send_message` — fire and forget, swallows everything. |
| `invite_tokens.py` | HMAC-signed self-contained invite tokens. Fully tested but **not currently wired to any route**; the live flow uses `partner_invites` rows instead. |

### Time handling
All DB columns are `TIMESTAMP` without time zone. The application works
in UTC and strips the offset before writing:

```python
expires_at = naive_utc(utc_in_seconds(Config.SESSION_TTL_SECONDS))
```

SQL comparisons use `NOW() AT TIME ZONE 'utc'` to match. Writing a
tz-aware datetime, or comparing against bare `NOW()`, produces an
offset bug that only shows up away from UTC.

One inconsistency: `auth/user_id_login.py` writes
`utcnow_plus_seconds(...)` — a **tz-aware** value — where the OTP and
Mini App paths write `naive_utc(...)`. psycopg2 adapts it, but the two
paths are not writing the same thing.

### Caching and invalidation
Cache keys and TTLs are listed in `architecture.md`. The rule when
writing a mutation:

- Categories, types, seedlings, sales → `invalidate_dashboard_cache(u_id)`
- Partners → `_invalidate_partners(u_id)` for **both** users, which
  clears `partners_`, `partner_dashboards_` and `settings_`
- Sessions → `invalidate_session_cache(token_hash)` plus
  `sessions_<u_id>` and `settings_<u_id>`

A write without its invalidation leaves the dashboard showing stale
data for up to 60 seconds, which reads as "my change didn't save".

## Concurrency

`api/dashboard.py` runs the dashboard's five queries on a module-level
`ThreadPoolExecutor` sized `max(2, DB_POOL_MAX // 2)` — deliberately
below the pool size, since more workers than connections would just
queue.

`auth/user_id_login.py` has a 100-worker executor that writes the
session row after the response is sent, so login does not wait on the
ip-api.com lookup. Failures are logged and dropped, which means that
route can return a token whose session row was never written.

## House style

- Return through `ok()` / `fail()`. Never a bare dict.
- Validate explicitly: `if not isinstance(u_id, int): return fail(...)`.
- Give failures a `code` — clients branch on it.
- Scope every session query by `g.u_id`.
- Pass `timeout=` to every outbound HTTP call.
- Parameterise every query. If the number of placeholders must vary,
  build only the placeholders and pass values as params — see
  `partner_dashboards`.
