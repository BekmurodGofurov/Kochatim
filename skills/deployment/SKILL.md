---
name: kochatim-deployment
description: Rules for Kochatim's Docker Compose deployment. Use whenever editing docker-compose.yml, a Dockerfile, nginx.conf, or anything about running the stack on a server. Covers which ports may be published (the admin panel has no auth and the DB must stay on loopback), that the client's API URL is a build arg so changing it needs a rebuild, the Redis password shared between two .env files, the gunicorn worker requirements per service, and the three things to fix before exposing this to the internet.
---

# Kochatim Deployment Rules

One host, one Compose file, six containers, no orchestrator. Apply
these whenever touching `docker-compose.yml`, a Dockerfile, or
`nginx.conf`.

## Port exposure is a security decision

| Service | Current | Rule |
|---|---|---|
| `db` | `127.0.0.1:5432` | **Keep it on loopback.** Never `5432:5432`. |
| `redis` | not published | **Keep it unpublished.** It holds session cache entries. |
| `backend` | `8000` | Behind TLS in production. |
| `admin` | `9000` | **Should be loopback** — no authentication. |
| `client` | `80` | Behind TLS in production. |

Note the asymmetry: `db` is correctly bound to `127.0.0.1` but `admin`
is not, and `admin` has no authentication at all. Anything that can
reach port 9000 reads the traffic profile.

```yaml
admin:
  ports:
    - "127.0.0.1:9000:9000"   # then reach it over an SSH tunnel
```

`ssh -L 9000:127.0.0.1:9000 user@host`

**Never add a published port without asking what authenticates it.**

## Three things before this faces the internet

Full detail in `docs/security.md`; this is the deployment view.

1. **`POST /auth/user-id-login` must go.** It issues a valid 30-day
   session for any known Telegram ID with no authentication. A firewall
   cannot mitigate it — the endpoint is meant to be public.
2. **Port 9000 must not be published** (above).
3. **TLS must terminate in front.** Session tokens travel in an
   `Authorization` header and are readable in transit over plain HTTP.

Also set `DB_POOL_MAX` to 20 or lower — see below.

## The client's API URL is a build arg

```yaml
client:
  build:
    context: ./client
    args:
      VITE_API_BASE_URL: ${PUBLIC_URL:-http://localhost:8000}
```

Vite inlines `import.meta.env` at build time, so this value is baked
into the JavaScript bundle. Changing `PUBLIC_URL` requires:

```bash
docker compose up -d --build client
```

**Restarting the container does nothing.** This is the most common
deployment mistake in this repo. Adding it as an `environment:` entry
instead would not work either.

## The Redis password lives in two files

```yaml
redis:
  env_file: [./admin/.env]
  command: ["sh", "-c", "exec redis-server --requirepass \"$$REDIS_PASSWORD\""]
```

The `redis` container takes its password from `admin/.env`.
`backend/.env` must carry the **same** `REDIS_PASSWORD`, or the backend
gets `NOAUTH` on every cache call — and because `utils/cache.py`
swallows its own errors, it degrades *silently*. Symptom: everything
works but every request is slow and the admin panel shows zeroes.

If you change the password, change it in both files and recreate both
containers.

`$$` is Compose escaping: it passes a literal `$` through so the shell
inside the container expands the variable, rather than Compose
expanding it at parse time. Keep it when editing that line.

## Worker counts are not interchangeable

### backend — 4 workers
```dockerfile
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

Serves `app:app` — the **module-level** app object. That matters: the
CORS handlers and the request-stats recorder are registered on it
rather than inside `create_app()`, so a different entry point would
serve an app with neither.

> **`DB_POOL_MAX` is per worker.** 4 workers × the default 100 asks for
> 400 connections against Postgres's default `max_connections` of 100.
> Set it to 20 or lower in `backend/.env`.

All four workers also run `init_db()` on start. One wins a Redis lock
and the rest skip; if Redis is down all four run, which is safe only
because every DDL statement is idempotent. Keep it that way.

### admin — exactly 1 worker, gevent-websocket
```dockerfile
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "-w", "1", "-b", "0.0.0.0:9000", "app:app"]
```

Both parts are load-bearing:

- **One worker.** Each worker runs its own `redis_listener` thread and
  emits only to its own connected clients, so two workers means half
  the browsers miss half the updates.
- **The gevent-websocket worker.** It monkey-patches the process
  *before* the app module is imported, which is what lets the blocking
  `pubsub.listen()` loop cooperate with the event loop. Plain gunicorn,
  or `socketio.run(async_mode="gevent")` directly, hits a blocking-call
  problem.

### bot — a single polling process
`CMD ["python", "app.py"]`. Long polling, so **never scale it**. Two
instances would both poll `getUpdates` and each handle a random half of
the messages.

## Dependency ordering

`db` and `redis` have healthchecks and `backend` waits with
`condition: service_healthy`. `bot` uses a plain
`depends_on: [backend]`, which waits for the container to *start*, not
to be ready — hence a few failed calls in the bot's log on a cold boot.
Harmless with long polling.

If you add a service that needs the backend to be ready, give the
backend a healthcheck on `/health` and depend on that rather than
adding a sleep.

## nginx serves files, it does not proxy the API

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

That is the SPA fallback, so client-side routes survive a hard refresh.
The browser calls the backend directly, which is why
`ALLOWED_ORIGINS` must list the client's origin.

If you add an `/api` proxy, two things follow: the CORS requirement
disappears, and `VITE_API_BASE_URL` must become relative — which needs
a change in `https.js`, since `apiFetch` currently throws on an empty
`API_BASE`.

Any proxy you add must forward `X-Forwarded-For`.
`utils/device.py:get_client_ip` reads it first and falls back to
`remote_addr`; without it every session row records the proxy's IP.

## Schema changes need no deploy step

`db_init.py` runs on every backend start. There is no migration
command, so a deploy is just:

```bash
git pull
docker compose up -d --build
curl -s localhost:8000/health
```

Adding a column means editing **two** places in `db_init.py` — the
`CREATE TABLE` body and an `ALTER TABLE ... IF NOT EXISTS`. See
`skills/backend/SKILL.md`.

## Volumes and backups

| Volume | Holds | Losing it |
|---|---|---|
| `pgdata` | All application data | Total data loss |
| `redisdata` | Cache, counters, lock | Traffic history only |

Nothing is automated:

```bash
docker compose exec -T db pg_dump -U kochatim kochatim | gzip > backup-$(date +%F).sql.gz
```

Never add a bind mount over `pgdata` without migrating the data first.

## Test runners are separate

`docker-compose.test.yml` holds four runners on the same base images as
the services. They mount the repo **read-only**, declare no database
and no Redis, and share nothing with the running stack:

```bash
./scripts/test.sh --docker
```

Safe to run on the deployment host. When adding a runner, match its
base image to the service's Dockerfile — that is what makes the bot's
aiogram tests runnable at all, since aiogram 2.x will not install on
3.12+.

## Never commit

`.env` files, any real credential, or `hacking_map.md` (a working
exploit guide for the issues above, in a public repository). Every
service has a committed `.env.example`; add new settings there with
placeholders and document them in `docs/setup.md`.
