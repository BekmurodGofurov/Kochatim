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

`DB_POOL_MAX` now defaults to 20: 4 workers × 20 = 80, under Postgres's
default `max_connections` of 100. Raise it only together with
`max_connections`. (A `backend/.env` that still sets a larger value wins
over the default — check yours.)

## Middleware

### `client_gate` (a `before_request` hook, registered in `create_app()`)
Runs before every route, including unknown ones. Accepts `X-API-KEY`
(`Config.API_KEY`, sets `g.client = "bot"`) or `X-Client-Key`
(`Config.WEB_CLIENT_KEY`, sets `g.client = "web"`) and otherwise returns
the same bare `401 UNAUTHORIZED`. Exempt: `OPTIONS` and `GET /health`.
`?k=` is accepted as the web key on `GET /api/img/<file_id>` only,
because `<img src>` cannot send headers. Keys are compared with
`safe_equal`, and a blank header never matches an unset key.

The web key is public (it is in the browser bundle); the gate's job is
to keep scanners out and to tell the two callers apart.

### `require_api_key`
Bot-only. Compares `X-API-KEY` against `Config.API_KEY` in constant
time (`safe_equal`) and ignores `X-Client-Key` entirely. Returns
`500 SERVER_MISCONFIG` if the server has no key configured, and
`401 UNAUTHORIZED` otherwise. It re-checks the key itself instead of
trusting `g.client`, so the route stays safe even if the gate were ever
removed.

### `require_session`
Web-only (`g.client == "web"`). In order:

1. `Authorization: Bearer <token>` → `sha256_hex` → the session, from
   Redis `session_<token_hash>` (120s) or Postgres (filtered by
   `expires_at > NOW() AT TIME ZONE 'utc'`). The cached value is a dict
   `{u_id, device_key, ua_fp}`; an old bare-`u_id` entry counts as a miss.
   A session with no `device_key` is never honoured.
2. `X-Session-Proof` verified against the session's public key
   (`utils/device_proof.verify_proof`): fresh within
   `PROOF_MAX_SKEW_SECONDS`, correct signature over method +
   **raw request target** (`RAW_URI` from gunicorn, so percent-encoding
   matches what the browser signed) + nonce + token hash.
3. The nonce is claimed once in Redis (`claim_once`, `SET NX EX`). If
   Redis is down the check is skipped and logged — the timestamp window
   still bounds a replay.
4. Only after the signature has proved the caller holds the key: the
   browser/OS family must match the one at login, else the session is
   deleted (`revoke_session`) and the request is refused. Done last so a
   thief with a stolen token cannot log the victim out by sending an odd
   `User-Agent`.

Every failure is the same `401 UNAUTHORIZED`; the reason goes to the log.
Sets `g.u_id` and `g.token_hash`. **`g.u_id` is the only trustworthy
identity on a session route** — never take `u_id` from the request body
there.

`get_viewer()` runs the same checks but returns `None` instead of
rejecting, for public routes that show more to a signed-in viewer.

`revoke_session(token_hash, u_id)` deletes the row and every cache entry
that could still vouch for it; `invalidate_session_cache(token_hash)` is
the lighter form `DELETE /api/sessions/<id>` uses.

### Creating a session — `auth/session_service.py`
`create_session(u_id, device_key)` is the only place a session is
inserted (both `verify-code` and `telegram-webapp` call it).
`parse_device_key` validates the browser's public JWK first (EC P-256,
on the curve, no private part) and is called *before* a one-time code is
spent. IP and browser come from the Flask request inside the function —
there is deliberately no parameter to pass them in.

## `utils/`

| Module | Contents |
|---|---|
| `errors.py` | `ok(data, status)` / `fail(message, status, code, extra)` — the only two response shapes. |
| `security.py` | Token generation (`secrets`), `sha256_hex`, `safe_equal` (constant-time), Telegram `initData` HMAC verification (with an `auth_date` freshness check), `parse_telegram_user`. |
| `device_proof.py` | Pure crypto for device-bound sessions: `normalize_public_jwk`, `jwk_thumbprint`, `verify_proof`. No Flask, no Redis. |
| `ratelimit.py` | Fixed-window counters in Redis: `count`, `record`, `retry_after`. Return `None` when Redis is down so the caller chooses open or closed. |
| `time.py` | `utcnow()`, `utc_in_seconds()`, `naive_utc()`. |
| `cache.py` | Redis-backed cache. Every function swallows its own exceptions and degrades to a miss. `claim_once(key, ttl)` is the atomic single-use claim behind replay protection (`True` / `False` / `None` if Redis is down). |
| `device.py` | User-Agent parsing (`parse_device`, `client_fingerprint`), `get_client_ip` and `get_city`. `get_client_ip` trusts the TCP peer, and `X-Real-IP` only from a `TRUSTED_PROXIES` peer; it never reads `X-Forwarded-For`, and returns `""` for anything that is not a valid IP. `get_city` only looks up public addresses. |
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

`db.transaction()` is the way to write several rows as one unit (the
sale and its stock change). It does not retry on a dropped connection,
unlike `execute`/`fetch_*`: replaying half a transaction is not safe.

## House style

- Return through `ok()` / `fail()`. Never a bare dict.
- Validate explicitly: `if not isinstance(u_id, int): return fail(...)`.
- Give failures a `code` — clients branch on it.
- Scope every session query by `g.u_id`.
- Pass `timeout=` to every outbound HTTP call.
- Parameterise every query. If the number of placeholders must vary,
  build only the placeholders and pass values as params — see
  `partner_dashboards`.
