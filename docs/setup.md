# Local Setup

## Prerequisites

- Docker + Docker Compose v2. The whole stack is designed to run with
  `docker compose up`.
- A Telegram bot token from [@BotFather](https://t.me/BotFather). The
  bot will not start without one — `bot/data/config.py` raises at
  import.
- An [ImgBB](https://api.imgbb.com/) API key for variety photos.
  Without it uploads fail, but the rest of the app works.
- Only needed to run services **outside** Docker: Python 3.11 (the
  Dockerfiles pin `python:3.11-slim`; aiogram 2.x does not install on
  3.12+) and Node 20 for the client.

## 1. Configure environment

There are five `.env` files, one per service plus the root. Each has a
committed `.env.example`.

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp admin/.env.example admin/.env
cp bot/.env.example bot/.env
cp client/.env.example client/.env
```

### Root `.env` — provisions the Postgres container

| Variable | Notes |
|---|---|
| `POSTGRES_USER` | default `kochatim` |
| `POSTGRES_PASSWORD` | **change it** |
| `POSTGRES_DB` | default `kochatim` |
| `PUBLIC_URL` | where the browser reaches the backend. Baked into the client at build time. |

### `backend/.env`

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Inside Compose the host is `db`. Credentials must match the root `.env`. |
| `API_KEY` | yes | Shared secret for the bot. Must match `bot/.env`. |
| `BOT_TOKEN` | yes | Used to verify Mini App `initData` and to proxy Telegram images. |
| `TG_BOT_USERNAME` | yes | Used to build partner invite deep links. |
| `IMGBB_API_KEY` | no | Photo uploads fail without it. |
| `ALLOWED_ORIGINS` | yes | Comma-separated. **An empty value rejects every browser request** — there is no wildcard fallback. |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | yes | Host is `redis` inside Compose. |
| `ADMINS` | no | Comma-separated Telegram IDs that get CPU/RAM alerts. |
| `OTP_TTL_SECONDS` | no | default 120 |
| `SESSION_TTL_SECONDS` | no | default 2592000 (30 days) |
| `DB_POOL_MIN` / `DB_POOL_MAX` | no | defaults 5 / 100. See the warning below. |
| `FLASK_ENV` | no | default `production`. Anything else enables debug. |
| `SERVER_NAME` | no | Label shown in `/health` and the monitoring feed. |

> **`DB_POOL_MAX` is per worker.** Gunicorn runs 4 workers, so the real
> ceiling is `4 × DB_POOL_MAX` connections. The default 100 means 400,
> which exceeds Postgres's default `max_connections` of 100. Set it to
> 20 or lower for a single-host deployment.

### `bot/.env`

| Variable | Required | Notes |
|---|---|---|
| `BOT_TOKEN` | yes | Same token as the backend. |
| `API_URL` | yes | `http://backend:8000` inside Compose. |
| `API_KEY` | yes | Must match `backend/.env`. |
| `WEB_URL` | yes | Where the gardener opens the dashboard. |
| `ADMINS` | no | Comma-separated IDs for startup notifications. |

All four of the required ones raise `RuntimeError` at import if unset.
That is deliberate — a bot running without a token would look healthy
while doing nothing.

### `admin/.env`
`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `PORT`. The Redis
password is also read by the `redis` container itself, which is why
`docker-compose.yml` loads this file for that service.

### `client/.env`
`VITE_API_BASE_URL` and `VITE_TG_BOT_USERNAME`. Vite inlines these at
**build** time, so changing them needs a rebuild, not a restart.

## 2. Start the stack

```bash
docker compose up --build
```

`docker compose up` starts the production shape: no `client`
container, and nothing published to the network — on a server, ports
80/443 belong to the host's nginx. To run the frontend in Docker too,
add the `local` profile:

```bash
docker compose --profile local up --build
```

| Service | URL |
|---|---|
| client | http://localhost:8080 (profile `local` only) |
| backend | http://localhost:8000/health |
| admin | http://localhost:9000 |
| postgres | `127.0.0.1:5432` |

`backend` and `admin` are bound to `127.0.0.1`, so they are reachable
from the host but not from the network. Locally that is all you need;
no reverse proxy is involved.

The backend creates its own schema on first start — there is no
migration step to run. See `database.md`.

> The admin panel has **no authentication**. It is bound to
> `127.0.0.1` in `docker-compose.yml` for that reason — do not widen
> it. On a server, reach it with
> `ssh -L 9000:127.0.0.1:9000 admin@<host>`. See `security.md`.

## 3. Verify

```bash
curl http://localhost:8000/health
# {"ok":true,"data":{"status":"up","server":"server"}}
```

On a server, go through nginx instead:

```bash
curl -I https://api.kochatim.uz/health
```

Then open the bot in Telegram and send `/start`. If the bot answers and
`/health` is up, the two halves are talking.

## Running a service outside Docker

Useful for the backend while iterating. Keep `db` and `redis` in
Docker and point the backend at them on localhost.

```bash
docker compose up -d db redis

cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
# set DATABASE_URL to 127.0.0.1:5432 and REDIS_HOST to 127.0.0.1
.venv/bin/python app.py
```

`app.py` run directly uses Flask's dev server with debug on when
`FLASK_ENV != production`. Production uses gunicorn with 4 workers.

For the client:

```bash
cd client
npm ci
npm run dev        # port 5174, see vite.config.js
```

Add `http://localhost:5174` to `ALLOWED_ORIGINS` in `backend/.env`, or
every request will be blocked by CORS.

## Running the tests

```bash
./scripts/test.sh              # all four suites
./scripts/test.sh --docker     # inside the service base images
./scripts/test.sh backend      # just one
```

The suites need no database and no Redis — the DB layer is mocked at
the pool boundary and the cache runs on `fakeredis`. Local mode needs:

```bash
pip install -r backend/requirements.txt -r test/requirements-test.txt
cd client && npm ci
```

Use `--docker` to run the bot's aiogram tests, which cannot run on
Python 3.13. See `testing.md`.

## Common problems

**Backend exits immediately with a connection error.** `db` was not
ready. It has a healthcheck and the backend `depends_on` it with
`condition: service_healthy`, so this usually means the credentials in
`backend/.env` do not match the root `.env`.

**Every browser request fails with a CORS error.** The client's origin
is not in `ALLOWED_ORIGINS`. The response carries
`Access-Control-Allow-Origin: null` — that is the rejection, not a bug.

**The bot container restarts in a loop.** A required variable is
missing from `bot/.env`; the container logs which one.

**Redis `NOAUTH` errors.** `docker-compose.yml` starts Redis with
`--requirepass $REDIS_PASSWORD` from `admin/.env`. If you set a
password there, set the same value in `backend/.env`.

**Photos never appear.** Check `IMGBB_API_KEY`. `img.i_url` can also
hold a bare Telegram `file_id`, which renders through the
`/api/img/<file_id>` proxy and so needs `BOT_TOKEN` set.
