# Database

PostgreSQL 16. No ORM — every query is hand-written SQL through
`psycopg2`, routed through `backend/db.py`. No migration tool either;
the schema is created and evolved by `backend/db_init.py` on startup.

## Tables

### `users`
The gardener. `u_id` is the Telegram user ID, used as the primary key
throughout — there is no separate internal ID.

| Column | Type | Notes |
|---|---|---|
| `u_id` | `BIGINT PK` | Telegram user ID. Not secret. |
| `u_name` | `TEXT` | |
| `u_phone` | `TEXT` | Presence of this is treated as "registered". |
| `u_username` | `TEXT` | Telegram @username, without the `@`. |
| `u_age` | `INTEGER` | |
| `u_photo` | `TEXT` | Added later by migration. |
| `added_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | Maintained by trigger. |

### `categories` — plant groups
| Column | Type | Notes |
|---|---|---|
| `c_id` | `SERIAL PK` | |
| `u_id` | `BIGINT` | Owner. No FK constraint. |
| `c_name` | `TEXT` | Unique per user by convention, not by constraint. |
| `added_at` / `updated_at` | `TIMESTAMP` | |

### `types` — varieties within a group
| Column | Type | Notes |
|---|---|---|
| `t_id` | `SERIAL PK` | |
| `u_id` | `BIGINT` | Owner. |
| `c_id` | `INTEGER` | Parent category. No FK. |
| `t_name` | `TEXT` | |
| `deff` | `TEXT` | Description. The name is a typo for "def(inition)" that is now load-bearing — the client also probes `description`, `t_desc` and `t_deff` as fallbacks. |
| `added_at` / `updated_at` | `TIMESTAMP` | |

### `seedlings` — stock
One row per (user, variety). Three quality grades as separate columns.

| Column | Type | Notes |
|---|---|---|
| `s_id` | `SERIAL PK` | |
| `u_id` | `BIGINT` | |
| `t_id` | `INTEGER` | |
| `quality_1` / `quality_2` / `quality_3` | `INTEGER DEFAULT 0` | |
| `added_at` / `updated_at` | `TIMESTAMP` | |

There is no unique constraint on `(u_id, t_id)`, so a race between two
concurrent "set stock" calls can create duplicate rows. Reads use
`fetch_one`, so only one would then be visible.

### `seedlings_logs` — audit trail of stock changes
Written by `POST /api/seedlings/update`. Records the delta, not the
resulting total.

| Column | Type |
|---|---|
| `log_id` | `SERIAL PK` |
| `u_id` | `BIGINT NOT NULL` |
| `t_id` | `INTEGER NOT NULL` |
| `change_q1` / `change_q2` / `change_q3` | `INTEGER DEFAULT 0` |
| `price` | `REAL DEFAULT 0` |
| `comment` | `TEXT` |
| `created_at` | `TIMESTAMP` |

### `sales`
| Column | Type | Notes |
|---|---|---|
| `sale_id` | `SERIAL PK` | |
| `u_id` / `c_id` / `t_id` | | |
| `q1_sold` / `q2_sold` / `q3_sold` | `INTEGER DEFAULT 0` | |
| `price` | `REAL` | Total for the sale, not a unit price. `REAL` is a float — fine for display, not for accounting. |
| `sold_at` | `TIMESTAMP` | |

### `img`
| Column | Type | Notes |
|---|---|---|
| `i_id` | `SERIAL PK` | |
| `t_id` | `INTEGER` | |
| `i_url` | `TEXT` | Either an `https://` URL (ImgBB) **or** a bare Telegram `file_id`, when conversion failed. Readers must handle both. |
| `added_at` / `updated_at` | `TIMESTAMP` | |

Dashboard queries take the newest row per type via
`LEFT JOIN LATERAL (... ORDER BY i_id DESC LIMIT 1)`, so multiple rows
per type are tolerated and the latest wins.

### `login_codes` — OTP
| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PK` | |
| `code_hash` | `TEXT NOT NULL` | SHA-256 of the 6 digits. The code is never stored in plaintext. |
| `u_id` | `BIGINT NOT NULL` | |
| `expires_at` | `TIMESTAMP NOT NULL` | 120s by default. |
| `used_at` | `TIMESTAMP` | Set on use; single-use enforced in code. |
| `created_at` | `TIMESTAMP` | |

Rows are never deleted. The table grows forever — worth a cleanup job.

### `sessions`
| Column | Type | Notes |
|---|---|---|
| `token_hash` | `TEXT PK` | SHA-256 of the bearer token. |
| `u_id` | `BIGINT NOT NULL` | |
| `expires_at` | `TIMESTAMP NOT NULL` | 30 days by default. |
| `session_id` | `SERIAL` | Added by migration. Used in the delete-session URL so the token hash never appears in one. |
| `device_name` / `ip_address` / `city` | `TEXT DEFAULT ''` | Added by migration. Backfilled lazily on first `GET /api/sessions`. |
| `created_at` | `TIMESTAMP` | |

Capped at 3 per user in application code, not by constraint. Expired
rows are filtered on read (`expires_at > NOW() AT TIME ZONE 'utc'`) but
never deleted.

### `partners`
| Column | Type |
|---|---|
| `u_id` | `BIGINT NOT NULL` |
| `p_id` | `BIGINT NOT NULL` |
| `created_at` | `TIMESTAMP` |
| | `PRIMARY KEY (u_id, p_id)` |

Symmetric: accepting an invite inserts **both** `(a, b)` and `(b, a)`.
Removal deletes both directions in one statement. Any code that adds a
partnership must insert both rows, or the relationship will look
one-sided.

### `partner_invites`
| Column | Type | Notes |
|---|---|---|
| `token` | `VARCHAR(32) PK` | `secrets.token_urlsafe(18)` — 24 chars, URL-safe for a Telegram deep link. |
| `inviter_u_id` | `BIGINT NOT NULL` | |
| `expires_at` | `TIMESTAMP NOT NULL` | 7 days. |
| `used_at` | `TIMESTAMP` | Set on accept. **Not** set on decline. |
| `created_at` | `TIMESTAMP` | |

## No foreign keys

Nothing in the schema declares a foreign key. Deleting a category
leaves its types; deleting a type leaves its seedlings, sales rows and
images. Ownership is enforced in `WHERE u_id = %s` clauses instead.

Two consequences:

- A query that forgets `u_id` reads across users. That is the IDOR
  shape to watch for in review.
- Orphan rows accumulate. Reads join with `LEFT JOIN`, so an orphaned
  `seedlings` row shows up with `t_name: null` rather than disappearing.

## Timestamps

`updated_at` is maintained by a trigger on `users`, `categories`,
`types`, `seedlings` and `img`:

```sql
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
```

All columns are `TIMESTAMP` (no time zone). The application generates
UTC and strips the offset with `utils/time.py:naive_utc()` before
writing. Comparisons in SQL use `NOW() AT TIME ZONE 'utc'` to match.
Writing a tz-aware datetime directly, or using bare `NOW()`, will
produce an offset bug.

## Indexes

Created by `init_db()`:

```
categories (u_id)          seedlings (u_id)        sales (u_id)
types (u_id)               seedlings (t_id)        sales (c_id)
types (c_id)               img (t_id)              sales (t_id)
types (u_id, t_id DESC)    img (t_id, i_id DESC)
sessions (u_id)            partners (u_id)         partners (p_id)
```

The two composite indexes exist for the `LEFT JOIN LATERAL` lookups in
the dashboard queries. There is no index on
`login_codes (code_hash)` — OTP verification does a sequential scan on
a table that is never pruned.

## The db layer

`backend/db.py` is the only place that talks to the pool.

| Function | Commits | Returns |
|---|---|---|
| `execute(q, params)` | yes | `None` |
| `execute_returning(q, params)` | yes | one row as `dict`, or `None` |
| `fetch_one(q, params)` | no | one row as `dict`, or `None` |
| `fetch_all(q, params)` | no | `list[dict]`, `[]` when empty |

Each retries **once** on a dropped connection — the error messages
listed in `_is_retryable_db_error` plus `psycopg2.OperationalError` and
`InterfaceError`. A retryable failure returns the connection with
`put_conn(conn, close=True)` so the pool discards it; handing a dead
socket back for reuse is the bug that logic exists to prevent. Errors
that are not transient (`ProgrammingError`, `IntegrityError`) raise
immediately — retrying a syntax error is pointless.

Connections come from a `ThreadedConnectionPool` sized by
`DB_POOL_MIN` / `DB_POOL_MAX`. `DB_POOL_MAX` must account for 4
gunicorn workers plus the dashboard thread pool: the real ceiling is
`workers × DB_POOL_MAX`, which must stay under Postgres's
`max_connections`.
