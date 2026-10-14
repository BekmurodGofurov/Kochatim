# Security — Status of Known Issues

This is a remediation record, not a threat report. It deliberately
describes **what changed and why** rather than how to exploit anything,
because this repository is public and the application is live.

The working audit notes that go into attack detail live in
`hacking_map.md` and `hacking_map_advanced.md`, which are gitignored and
must stay that way.

Each item below says **Fixed** (with the file that now enforces it and the
test that guards it) or **Open**.

---

## How access is controlled now

```
request ─► client gate ─► route decorator ─► handler
           key present?    bot key / session +
           (else bare 401) device proof
```

1. **Client gate** (`middleware/client_gate.py`). Every request needs the
   bot key (`X-API-KEY`) or the web client key (`X-Client-Key`); otherwise
   it gets the same bare 401 whatever the path, so the API cannot be
   mapped from outside. Only `/health` and CORS preflights are exempt.
2. **Privilege separation.** Bot routes accept the bot key only, session
   routes accept the web client only. The web key is **public** (it is in
   the browser bundle), so it must never open a route that takes `u_id`
   from the caller.
3. **Device-bound sessions** (`middleware/require_session.py`,
   `utils/device_proof.py`). A session token works only together with a
   per-request signature from a key the browser generated at login and
   cannot export.

What the web key is and is not: it stops scanners, bots and `curl`. It
does not stop someone who opens DevTools. The protection of user data
comes from layers 2 and 3 and from not returning private data on open
routes.

---

## Fixed

### 1. `POST /auth/user-id-login` issued sessions without authentication — **was critical**
The endpoint accepted a `u_id`, confirmed the user existed, and returned a
30-day session. A Telegram user ID is not a secret, so this was full
account takeover.

**Fix.** The route and `auth/user_id_login.py` are deleted. A session can
now only come from `POST /auth/verify-code` (an OTP the bot delivered over
Telegram) or `POST /auth/telegram-webapp` (HMAC-verified `initData`), both
through `auth/session_service.create_session`, and both require the
browser's device key. Existing sessions were revoked: `db_init.py` deletes
every session without a device key, which includes any token ever minted
by the old route.
*Tests:* `test_auth.py::TestUserIdLoginIsGone`.

### 2. A copied session token worked anywhere — **was high**
The token sat in `localStorage` and was a complete credential on its own.

**Fix.** Sessions are bound to an ECDSA P-256 key pair the browser creates
at login with `extractable=false`. Every request carries `X-Session-Proof`:
a signature over method, path+query, a nonce and the token's hash. Proofs
expire after `PROOF_MAX_SKEW_SECONDS` and are single-use. A different
browser or OS family than the one the session was created from also ends
the session.
Limits: script running *inside* the page can still ask the browser to
sign, so XSS is not neutralised — it only cannot take the key away. See
the CSP note under *Open*.
*Tests:* `test_session_binding.py`, `test_device_proof.py`
(including a proof produced by the real JavaScript signer).

### 3. The API answered anyone — **was high**
No global access control; routes were public unless decorated.

**Fix.** The client gate above. `test_client_gate.py` iterates every
registered route and fails if one answers without a key, or if a route is
undecorated and not on the explicit public list.

### 4. The client's IP and browser could be forged — **was medium**
`get_client_ip` took the first `X-Forwarded-For` value, and nginx appended
to whatever the client sent, so session rows (and the "active sessions"
list a victim looks at) could show an attacker-chosen IP and city. The
value was also interpolated into a geolocation URL.

**Fix.** `utils/device.get_client_ip` believes only the TCP peer and, when
that peer is a configured trusted proxy (`TRUSTED_PROXIES`), the
`X-Real-IP` nginx sets. `X-Forwarded-For` is never read. The result must
parse as an IP, and only public addresses are geolocated. nginx now
**overwrites** `X-Forwarded-For`/`X-Real-IP` with `$remote_addr`. The
browser name comes from the `User-Agent` parsed on the server; no body or
query field can set an IP, browser, device name or city
(`create_session` has no parameter for them).
*Tests:* `test_device.py::TestGetClientIp`, `test_session_service.py`.

### 5. Unhandled exceptions returned internal detail — **was medium**
`str(e)` reached the client: SQL, DSN, and — through `requests` errors on
the image proxy — a URL containing the bot token.

**Fix.** The global handler logs and returns a fixed message; HTTP errors
keep their status. `public.py`, `telegram_webapp.py` and the image proxy
no longer return exception text. The proxy logs only the exception *type*.
*Tests:* `test_app.py::TestErrorHandlers`, and a "generic 500" test on
most routes.

### 6. Public endpoints returned phone numbers — **was medium**
`GET /api/gardeners` and `GET /api/users/<id>/dashboard`.

**Fix.** The directory returns `u_id` and `u_name` only. The profile returns
the name only, unless the viewer is signed in *and* is that gardener or one
of their partners, who see the full profile as before (`get_viewer`).
*Tests:* `test_users.py::TestGardeners`,
`test_dashboard.py::TestPublicDashboard`.

### 7. The admin panel had no authentication, and a stored XSS — **was high**
Anything that reached port 9000 read traffic data; request paths from
attackers were written into `innerHTML`.

**Fix.** HTTP Basic auth on every route (`ADMIN_USER` / `ADMIN_PASSWORD`,
constant-time, fail closed when unset), the same check on the Socket.IO
connect, same-origin WebSocket by default, no debug mode, a CSP and
security headers. The browser code builds the DOM with `textContent`. The
backend now records the *matched route pattern* (`/api/users/<int:u_id>/…`)
instead of the raw URL.
*Tests:* `admin/tests/test_admin_app.py`.

### 8. OTP guessing and reuse — **was high**
Six digits, two minutes, no attempt limit; a code could be redeemed twice
by parallel requests; two live users could hold the same code.

**Fix.** Wrong codes are counted per IP (5 / 10 min) and globally
(500 / 10 min) in Redis, with `429` and `Retry-After`; the check fails
closed when Redis is down. A code is spent by a single
`UPDATE … WHERE used_at IS NULL RETURNING`. New codes never collide with a
live one and retire the user's older ones. `login_codes.code_hash` is
indexed. nginx adds a request budget on `/auth/`.
*Tests:* `test_auth.py::TestVerifyCode`.

### 9. Telegram `initData` never expired — **was medium**
The HMAC was checked but `auth_date` was not, so a captured string logged in
forever.

**Fix.** `telegram_webapp_verify(..., max_age_seconds=INITDATA_MAX_AGE_SECONDS)`
refuses stale, future-dated and `auth_date`-less data.
*Tests:* `test_security.py::TestInitDataFreshness`.

### 10. Stock could go negative under parallel requests — **was medium**
`seedlings/update` read the level, checked it, then wrote.

**Fix.** One `UPDATE … WHERE level + change BETWEEN 0 AND cap RETURNING`
decides under the row lock. Quantities are validated (non-numbers are `400`,
not `500`). The same guard protects the bot's `seedlings/set`.
*Tests:* `test_seedlings.py` — including the real SQL run on SQLite to show
two parallel `-50`s against a stock of 60 cannot both succeed.

### 11. `POST /api/sales` had no transaction — **was low**
**Fix.** `db.transaction()` (one commit, rollback on any error); the stock
guard lives in the `UPDATE`, the sale row is inserted in the same
transaction. *Tests:* `test_sales.py`, `test_db.py::TestTransaction`.

### 12. `POST /api/types` did not check category ownership — **was low**
**Fix.** The category must belong to `u_id` (`404` otherwise).

### 13. `POST /api/partners/decline` left the invite usable — **was low**
**Fix.** Decline sets `used_at`, so a declined invite cannot be accepted.

### 14. Image proxy could be used to tie up workers — **was medium**
Unauthenticated, two slow Telegram calls per request.

**Fix.** It still has to be reachable by `<img>` (so it takes the web key as
`?k=`), but now: the id must already be stored as a user photo or variety
image (indexed lookup) before Telegram is contacted; each IP has a request
budget; Telegram errors become `502` without the URL; non-image and SVG
content and bodies over 10 MB are refused.

### 15. Housekeeping done
`DB_POOL_MAX` defaults to 20 per worker (was 100 × 4 workers against
Postgres' default limit of 100). Partner-invite links are signed with
`INVITE_SECRET` (falls back to `API_KEY`) so the bot key can be rotated
without invalidating them. The bot's HTTP client has a 15 s timeout.
A production backend refuses to boot with missing, equal or placeholder
keys. "Log out" now ends the session on the server too.

---

## Open

- **Expired rows are never pruned** from `sessions` and `login_codes`.
  Add a periodic cleanup.
- **`price` is `REAL`**, a float. Fine for display, wrong for money;
  `NUMERIC(12,2)` if sales figures ever need to reconcile.
- **Secrets in logs.** A few `print` calls in `utils/images_v2.py` log
  exception text that can contain the Telegram/ImgBB URL. Not returned to
  clients, but present in container logs.
- **Content-Security-Policy is report-only** (`client/public/_headers`).
  Watch the console, then enforce it. Until then an XSS bug in the client
  could drive requests from the victim's own browser, even though it could
  not exfiltrate the device key.
- **The OTP is delivered by the bot and sent in a response body** to the
  bot (`/auth/request-code`). That is by design, but it makes the bot key
  powerful: anyone holding it can request a code for any user. Keep it
  server-side only and rotate it if it may have leaked.
- **A global OTP lockout is also a lever.** After 500 wrong codes in ten
  minutes nobody can log in with a code until the window rolls over
  (existing sessions and the Mini App are unaffected). That trade is
  deliberate; tune `_FAIL_LIMIT_GLOBAL` in `auth/otp.py`.

## What is done well (do not undo)

- **Every query is parameterised.** `%s` placeholders with a params tuple;
  the two dynamically assembled queries vary only the *number* of
  placeholders.
- **Secrets are hashed at rest.** Session tokens and OTP codes are stored as
  SHA-256; the plaintext exists only in the response.
- **`secrets` is used for every token**, not `random`.
- **Comparisons are constant-time** (`hmac.compare_digest`) for keys, the
  Telegram HMAC, invite tokens and admin credentials.
- **Invite verification fails closed** with no secret configured.
- **CORS has no wildcard, and no credentials.** An unlisted origin gets the
  literal `"null"`; an empty `ALLOWED_ORIGINS` rejects everything.
- **The Telegram image proxy does not leak the bot token**, in responses or
  logs.

## Reporting

Found something not listed here? Open a private channel with the owner
rather than a public issue, and do not commit proof-of-concept code to this
repository.
