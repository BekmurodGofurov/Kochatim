# Security — Known Issues and Fixes

This is a remediation checklist, not a threat report. It deliberately
describes **what to change** rather than how to exploit anything,
because this repository is public and the application is live.

The working audit notes that go into attack detail live in
`hacking_map.md`, which is gitignored and must stay that way.

Priority order. The first two should be fixed before the next deploy.

---

## 1. `POST /auth/user-id-login` issues sessions without authentication

**Severity: critical — full account takeover.**
`backend/auth/user_id_login.py`

The endpoint accepts a `u_id`, confirms the user exists, and returns a
valid 30-day session token. There is no password, no OTP, no signature,
no proof of any kind. A Telegram user ID is not a secret — it is
visible to anyone the gardener has messaged, and `GET /api/gardeners`
hands them out publicly (issue 4).

Anyone who learns a `u_id` gets that gardener's full account:
inventory, sales history, partners, phone number.

**Fix — delete the route.** Two authenticated login paths already
exist and the client does not need a third:

- `POST /auth/telegram-webapp` verifies the Mini App `initData` HMAC
  against `BOT_TOKEN`. Cryptographically sound; use this.
- `POST /auth/request-code` / `verify-code` is the OTP flow. The bot
  delivers the code over Telegram, which proves control of the account.

If something still calls it, make it require the OTP flow instead.
Rate-limiting or logging it is not a fix — the endpoint is unauthenticated
by design and the design is the problem.

Afterwards, invalidate existing sessions: `DELETE FROM sessions;`
forces everyone to log in again, which is the only way to be sure no
token was minted this way.

---

## 2. The admin panel has no authentication

**Severity: high — information disclosure.**
`admin/app.py`

Neither `GET /` nor `GET /api/stats` checks anything. Whatever can
reach port 9000 reads the traffic profile: request volumes and the
ten most-used endpoints.

**Fix — two parts, do both.**

1. **Stop publishing the port.** In `docker-compose.yml`, bind it to
   loopback the way Postgres already is:

   ```yaml
   ports:
     - "127.0.0.1:9000:9000"
   ```

   Then reach it over an SSH tunnel:
   `ssh -L 9000:127.0.0.1:9000 user@host`.

2. **Add authentication anyway**, so the panel is not one Compose edit
   away from being public. HTTP basic auth against an
   `ADMIN_USER` / `ADMIN_PASSWORD` pair from `admin/.env` is enough,
   compared with `hmac.compare_digest`. The Socket.IO connection needs
   the same check — `socketio.on('connect')` should reject an
   unauthenticated session, or the live feed stays open.

`admin/tests/test_admin_app.py::test_needs_no_auth` records the current
behaviour. When you fix this, that test should be inverted.

---

## 3. Unhandled exceptions return internal detail

**Severity: medium — information disclosure.**
`backend/app.py`

```python
@app.errorhandler(Exception)
def server_error(e):
    return fail("Server error", 500, extra=str(e))
```

`str(e)` on a `psycopg2` error contains the failing SQL, and on a
connection error the DSN — host, database name, sometimes the user.
That reaches the client.

**Fix** — log it, do not return it:

```python
@app.errorhandler(Exception)
def server_error(e):
    app.logger.exception("Unhandled error")
    return fail("Server error", 500)
```

Note that `api/public.py` already does the right thing in its own
`except` block by returning a fixed message.

---

## 4. Two public endpoints return phone numbers

**Severity: medium — PII exposure.**
`backend/api/users.py:search_gardeners`,
`backend/api/dashboard.py:dashboard_user`

| Route | Returns |
|---|---|
| `GET /api/gardeners` | `u_id`, `u_name`, `u_username`, **`u_phone`**, `u_photo` |
| `GET /api/users/<u_id>/dashboard` | the same profile plus the full catalogue |

Neither has an auth decorator. Together they allow enumerating every
registered gardener's `u_id` and phone number — and the `u_id` is what
makes issue 1 exploitable at scale.

**Fix** — drop `u_phone` from both `SELECT` lists. A directory of
gardeners is a reasonable feature; a directory of phone numbers is not.
If the phone number is needed after a connection is made, serve it from
a `@require_session` route that checks the two users are partners.

`GET /api/v1/public/categories` is the model to follow: it selects only
`c_id AS id, c_name AS name`, with no `u_id`, specifically so the
public list cannot be scraped for identifiers.

---

## 5. `POST /api/sales` has no transaction

**Severity: low — data integrity.**
`backend/api/sales.py`

The `INSERT` into `sales` and the `UPDATE` of `seedlings` are two
separate commits. A crash or connection drop between them records a
sale without reducing stock.

**Fix** — one statement each way is not enough; they need to share a
transaction. That means a helper in `db.py` that yields a cursor for
several statements and commits once, since every current function
commits on its own.

---

## 6. `POST /api/types` does not check category ownership

**Severity: low — only reachable with the API key.**
`backend/api/types.py:create_type`

The session equivalent (`POST /api/types/me`) verifies that `c_id`
belongs to the caller. The API-key version does not, so a caller can
attach a variety to another gardener's group.

**Fix** — add the same `fetch_one("SELECT c_id FROM categories WHERE
c_id=%s AND u_id=%s")` check. Low severity only because the API key is
a trusted service credential; it becomes serious the moment that key
leaks.

---

## 7. `POST /api/partners/decline` leaves the invite usable

**Severity: low.**
`backend/api/partners.py:decline_partner_invite`

It looks the token up and reports success without setting `used_at`, so
a declined invite can still be accepted later.

**Fix** — set `used_at` on decline, the way `accept` does.

---

## 8. Housekeeping

- **`login_codes` and `sessions` are never pruned.** Both grow
  forever, and `login_codes` has no index on `code_hash`, so OTP
  verification does a sequential scan over a table that only gets
  bigger. Add the index and a cleanup job for expired rows.
- **`DB_POOL_MAX` defaults to 100 per worker**, and gunicorn runs 4 —
  400 connections against Postgres's default limit of 100. Set it to
  20 or lower. Not a vulnerability, but it is a self-inflicted outage
  under load.
- **`price` is `REAL`**, a float. Fine for display, wrong for money.
  `NUMERIC(12,2)` if sales figures ever need to reconcile.

---

## What is already done well

Worth stating, so none of it gets undone in the course of fixing the
above:

- **Every query is parameterised.** `%s` placeholders with a params
  tuple throughout — no string interpolation of user input anywhere.
  The two places that build SQL dynamically only vary the *number* of
  placeholders, never a value.
- **Secrets are hashed at rest.** Session tokens and OTP codes are
  stored as SHA-256; the plaintext exists only in the response.
- **`secrets` is used for every token**, not `random`.
- **Comparisons are constant-time** where it matters —
  `hmac.compare_digest` in `safe_equal` and in the invite-token
  verifier.
- **Invite verification fails closed.** With no `API_KEY` configured,
  `parse_partner_invite_token` rejects everything rather than
  accepting anything.
- **CORS has no wildcard.** An unlisted origin gets the literal
  `"null"`, never `*`, which would be unusable with credentials
  anyway. An empty `ALLOWED_ORIGINS` rejects everything rather than
  allowing everything.
- **The Telegram image proxy does not leak the bot token.** It is used
  server-side to resolve the file and never appears in a response.

## Reporting

Found something not listed here? Open a private channel with the
owner rather than a public issue, and do not commit proof-of-concept
code to this repository.
