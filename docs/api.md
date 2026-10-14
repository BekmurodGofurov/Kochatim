# API Reference

Base URL is the backend, port 8000. Every response has the same two
shapes:

```json
{ "ok": true,  "data": ... }
{ "ok": false, "error": { "message": "...", "code": "...", "extra": "..." } }
```

`code` is present on most failures and is what clients should branch
on. `extra` is no longer sent: an unhandled 500 is just
`{"ok": false, "error": {"message": "Server error"}}` and the detail goes
to the server log.

**`ok: false` can arrive with HTTP 200.** Both the bot's `api_client`
and the client's `apiFetch` check the `ok` field, not just the status.

## Authentication

**Every** request needs a key; without one the answer is the same bare
`401 UNAUTHORIZED` whatever the path (so unknown routes cannot be told
from real ones). Only `GET /health` and CORS preflights are exempt.

| Header | Who | What it unlocks |
|---|---|---|
| `X-API-KEY: <API_KEY>` | the bot | **key** routes. A service credential — the caller supplies `u_id` and so chooses whose data it touches. |
| `X-Client-Key: <WEB_CLIENT_KEY>` | the web client | **public** and **session** routes. *Not a secret* — it ships in the browser bundle. |

| Marker | Requires |
|---|---|
| **key** | `X-API-KEY` only. The web client key does not work here. |
| **session** | `X-Client-Key` **plus** `Authorization: Bearer <token>` **plus** `X-Session-Proof` (below). Identity comes from `g.u_id`; the body cannot override it. The bot key does not work here. |
| **public** | `X-Client-Key` (or, for the bot, `X-API-KEY`). No session. |

**`X-Session-Proof`** is `v1.<ts_ms>.<nonce>.<signature>`: an ECDSA
P-256 / SHA-256 signature (raw 64-byte `r||s`, base64url) over
`<ts>.<nonce>.<METHOD>.<path?query>.<sha256 hex of the token>`, made with
the key pair the browser generated at login. It is valid for
`PROOF_MAX_SKEW_SECONDS` (60) and once only. Without a valid proof the
token alone is rejected. See `client/src/api/deviceKey.js` and
`backend/utils/device_proof.py`.

Failures: `401 UNAUTHORIZED` for any missing or wrong credential (the
reason is logged, never returned), `429 RATE_LIMITED` (with
`Retry-After`), `500 SERVER_MISCONFIG` if `API_KEY` is unset.

## Auth routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/request-code` | key | Upserts the user, returns a 6-digit OTP and `expires_in`. Body: `{u_id, u_name?, u_username?, u_phone?, u_age?}`. `u_id` must be an `int`. |
| POST | `/auth/verify-code` | public | Body `{code, device_key}`. `device_key` is the browser's public JWK (`{kty:"EC", crv:"P-256", x, y}`). Returns `{session_token, u_id, expires_in}`. Codes: `INVALID_CODE`, `CODE_NOT_FOUND`, `CODE_USED`, `CODE_EXPIRED`, `DEVICE_KEY_REQUIRED`, `RATE_LIMITED` (5 wrong codes per IP per 10 min), `UNAVAILABLE` (503, Redis down). |
| POST | `/auth/telegram-webapp` | public | Body `{initData, device_key}`. Verifies the Telegram HMAC **and** that `auth_date` is at most `INITDATA_MAX_AGE_SECONDS` old. Returns `{session_token, u_id, is_registered}`. `INVALID_INITDATA`, `DEVICE_KEY_REQUIRED`. |

`/auth/user-id-login` no longer exists. A user id alone never yields a
session.

The OTP is stored as a SHA-256 hash with a 120s TTL and is spent by one
atomic `UPDATE`. A new code retires the user's earlier ones and never
collides with another live code. Session tokens are stored hashed; the
plaintext exists only in the response. The server records the caller's IP
and browser itself — no body or query field can set them. At most three
sessions per user; the oldest is dropped.

## User routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/me` | session | The caller's own profile. `404 NOT_FOUND` if the row is gone. |
| GET | `/api/me/settings` | session | Partners + sessions + invite token + bot username in one call. Cached 120s. Creates an invite token if none is live. |
| POST | `/api/users/ensure` | key | Upsert. `COALESCE` keeps existing values, so sending `null` preserves a field rather than clearing it. |
| GET | `/api/users/<u_id>` | key | Any user's profile, including `u_phone`. |
| GET | `/api/gardeners` | **public** | Search by `q` (exact `u_id` if numeric, else `ILIKE` on name/username), `limit` 1–50, default 12. Returns **`{u_id, u_name}` only** — no phone, username or photo. |

## Dashboard routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/me/dashboard` | session | user + categories + types + seedlings + sales summary. Five queries run concurrently on a thread pool. Cached 60s. |
| GET | `/api/partners/dashboards` | session | Every partner's inventory. Three bulk queries instead of N+1. Cached 300s. |
| GET | `/api/users/<u_id>/dashboard` | **public**, viewer-aware | Anonymous callers and signed-in strangers get `{user: {u_id, u_name}, categories: [], types: [], seedlings: [], restricted: true}`. The gardener themself and their partners (signed in, with a valid proof) get the full profile including `u_phone`, catalogue and stock. |

## Categories (plant groups)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/categories` | session | The caller's groups. |
| POST | `/api/categories/me` | session | Body `{c_name}`. `400 ALREADY_EXISTS` on a duplicate name. |
| GET | `/api/categories/by-user?u_id=` | key | |
| POST | `/api/categories` | key | Body `{u_id, c_name}`. Idempotent: an existing name returns `{created: false, c_id}`. |
| PUT | `/api/categories/<c_id>` | key | Body `{u_id, c_name}`. Scoped by `u_id` in the `WHERE`. |
| DELETE | `/api/categories/<c_id>?u_id=` | key | Scoped by `u_id`. |

Note the asymmetry: the session route rejects a duplicate name with an
error, the API-key route treats it as success. The bot relies on the
idempotent behaviour.

## Types (varieties)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/types/me` | session | Body `{c_id, t_name, deff?, image_url?}`. Verifies the category belongs to the caller (`404 NOT_FOUND`). `image_url` goes through `process_image_input`. |
| POST | `/api/types` | key | Body `{u_id, c_id, t_name, deff?}`. Does **not** verify category ownership. |
| GET | `/api/types?u_id=&c_id=` | key | Both filters optional. |
| GET | `/api/types/by-user?u_id=&c_id=` | key | Both required. |
| GET | `/api/types/<t_id>` | key | No ownership check — any `t_id`. |
| GET | `/api/types/by-id?u_id=&t_id=` | key | Scoped by `u_id`. |
| GET | `/api/type-info?u_id=&t_id=` | key | Name and description only. |
| PUT | `/api/types/<t_id>` | key | Body `{u_id, t_name, deff?}`. |
| DELETE | `/api/types/<t_id>?u_id=` | key | |

`_to_int()` in `api/types.py` accepts an `int`, a numeric string, or a
dict (pulling `c_id`/`t_id`/`u_id`/`id`/`value`) — the bot's keyboards
sometimes send the whole object.

## Seedlings (stock)

Stock is three integer columns: `quality_1`, `quality_2`, `quality_3`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/seedlings?t_id=` | session | Returns zeroes rather than 404 when there is no row. |
| POST | `/api/seedlings/update` | session | Body `{t_id, change_q1, change_q2, change_q3, comment?, price?}`. **Deltas, not absolutes.** Refuses to go negative (`400 INSUFFICIENT_STOCK`) and writes a `seedlings_logs` row. |
| GET | `/api/seedlings/count?u_id=&t_id=` | key | |
| POST | `/api/seedlings/set` | key | Body `{u_id, t_id, quality_1..3}`. Despite the name these are **added** to the current values, and no negative check is applied. |

## Sales

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/sales` | session | `{history: [...], pie: [...]}`. History is the latest 200, reshaped for the UI (`id`, `name`, `category`, `date`, `qty`, `price`). `pie` sums revenue per category. |
| POST | `/api/sales` | key | Body `{u_id, c_id, t_id, q1_sold, q2_sold, q3_sold, price}`. Verifies the type belongs to that user *and* category (`404 NOT_FOUND`), refuses to oversell (`400 INSUFFICIENT_STOCK`), then inserts and decrements stock. |

`POST /api/sales` is the one write that does two statements with no
transaction around them: the `INSERT` into `sales` and the `UPDATE` of
`seedlings` are separate commits. A crash between them records a sale
without reducing stock.

## Partners

A partnership is symmetric and stored as two rows in `partners`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/partners` | session | Cached 300s. |
| POST | `/api/partners/remove` | session | Body `{p_id}`. Deletes both directions and notifies the removed partner over Telegram. |
| GET | `/api/partners/invite-token` | session | Reuses a live token if there is one, else mints a 7-day token. Returns `{token, bot_username}`. Cached 1800s. |
| GET | `/api/users/<u_id>/partners` | key | |
| POST | `/api/partners/accept` | key | Body `{token, u_id}`. Codes: `INVALID_TOKEN`, `INVITE_USED`, `INVITE_EXPIRED`, `SELF`, `NOT_FOUND`. Already-partners returns `ok: true` with `already_partners: true`. |
| POST | `/api/partners/decline` | key | Body `{token, u_id}`. Marks the invite used, so it cannot be accepted afterwards. `INVALID_TOKEN`, `INVITE_USED`. |

Two token mechanisms exist. The live one is `generate_invite_token()`
plus a `partner_invites` row. `utils/invite_tokens.py` implements a
self-contained HMAC-signed token instead — it is fully tested but not
currently wired into any route.

## Sessions

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/sessions` | session | Device, city, IP, created-at and `is_current` per session. The cache holds no per-viewer state; `is_current` is computed for each request. Never returns token hashes. Cached 120s. |
| POST | `/api/logout` | session | Deletes the current session and its cache entries. The client also forgets its device key. |
| DELETE | `/api/sessions/<session_id>` | session | Scoped by `u_id`. Invalidates that token's cache entry, so logout is immediate rather than waiting out the 120s TTL. |

## Images

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/img` | key | Body `{t_id, i_url}`. Upsert on `t_id`. Runs `process_image_input`. |
| POST | `/api/img/upload` | session | `multipart/form-data`, field `image`. Uploads to ImgBB, returns `{url}`. `500` if ImgBB rejects it. |
| GET | `/api/img/by-type?t_id=` | key | Returns the URL, or `null` when there is no row. |
| GET | `/api/img/<file_id>?k=<client key>` | **public** | Resolves a Telegram `file_id` and streams the image. Cached a day. `<img src>` cannot send headers, so the web key may be given as `?k=` on this route only. Only ids stored as a user photo or variety image are fetched (`404` otherwise); 120 requests/min per IP (`429`); `502` if Telegram fails or returns something that is not an image or is over 10 MB. |

## Public and operational

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | none | `{status: "up"}` — nothing about the host. The only route that needs no key. Not counted in endpoint stats. |
| GET | `/api/v1/public/categories` | public | `{id, name}` only — deliberately no `u_id`, so the list cannot be scraped for Telegram IDs. |

## CORS

`_cors_origin()` echoes the request's `Origin` back only if it appears
in `ALLOWED_ORIGINS`, otherwise it returns the literal string `"null"`
— never `*`. An empty `ALLOWED_ORIGINS` rejects everything. No cookies
are used, so `Access-Control-Allow-Credentials` is not sent. Allowed
request headers: `Content-Type, Authorization, X-API-KEY, X-Client-Key,
X-Session-Proof`.

`OPTIONS` is answered with 204 in a `before_request` hook, and the client
gate lets it through (a preflight carries no custom headers), so
preflight never reaches an authenticated handler. CORS headers are added in
`after_request` and therefore appear on error responses too, which is
what lets the browser read a 401 body.

These hooks are registered on the module-level `app` object, **not**
inside `create_app()`. An app built by calling `create_app()` has no
CORS and no request stats. Gunicorn serves `app:app`, so production
gets the configured instance — but tests must use the same one.
