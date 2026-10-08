# Deployment

One host, one Docker Compose file, six containers. There is no load
balancer, no orchestrator, and no staging environment —
`docker-compose.yml` is the entire topology.

## Containers

| Service | Image | Published port | Notes |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `127.0.0.1:5432` | **Loopback only.** Correct — do not widen it. |
| `redis` | `redis:7-alpine` | none | Reachable only on the Docker network. |
| `backend` | built from `backend/` | `8000` | gunicorn, 4 workers |
| `admin` | built from `admin/` | `9000` | **No authentication — see below** |
| `bot` | built from `bot/` | none | Outbound long polling only |
| `client` | built from `client/` | `80` | nginx serving static files |

All on the `kochatim` bridge network, where services address each other
by name: `db`, `redis`, `backend`.

### Health checks and ordering

`db` and `redis` have healthchecks, and `backend` waits for both with
`condition: service_healthy`. `admin` waits for `redis`. `bot` uses a
plain `depends_on: [backend]`, which only waits for the container to
*start*, not to be ready — so on a cold boot the bot may make a few
failed calls before the backend is listening. Harmless with long
polling, but that is why those errors appear in the logs at startup.

### Redis password

```yaml
redis:
  env_file: [./admin/.env]
  command: ["sh", "-c", "exec redis-server --requirepass \"$$REDIS_PASSWORD\""]
  healthcheck:
    test: ["CMD-SHELL", "redis-cli --no-auth-warning -a \"$$REDIS_PASSWORD\" ping | grep -q PONG"]
```

The password comes from `admin/.env`, which is why the `redis` service
loads that file. `backend/.env` must carry the **same** `REDIS_PASSWORD`
or the backend gets `NOAUTH` on every cache call — which degrades
quietly, because `utils/cache.py` swallows its own errors. Symptom: the
app works but every request is slow and the admin panel shows zeroes.

The `$$` is Compose escaping — it passes a literal `$` to the shell so
the variable is expanded inside the container, not by Compose.

## Deploying

```bash
git pull
docker compose up -d --build
docker compose ps
curl -s localhost:8000/health
```

The backend creates and migrates its own schema on start
(`db_init.py`), so there is no migration step. Four gunicorn workers
would race, so one wins a Redis lock and the rest skip — see
`database.md`.

### The client is built, not configured

`VITE_API_BASE_URL` is a **build arg**, baked into the JavaScript:

```yaml
client:
  build:
    context: ./client
    args:
      VITE_API_BASE_URL: ${PUBLIC_URL:-http://localhost:8000}
```

Changing `PUBLIC_URL` therefore requires a rebuild:

```bash
docker compose up -d --build client
```

Restarting the container is not enough. This is the most common
deployment mistake here.

## Before exposing this to the internet

Three things must be dealt with first. The detail and the fixes are in
`security.md`; this is the deployment-side summary.

1. **Delete `POST /auth/user-id-login`.** It issues a valid session for
   any known Telegram ID with no authentication. This is not something
   a firewall can mitigate — the endpoint is meant to be public.

2. **Do not publish port 9000.** The admin panel has no auth and its
   Socket.IO feed accepts any origin. Change the mapping to loopback:

   ```yaml
   admin:
     ports:
       - "127.0.0.1:9000:9000"
   ```

   and reach it over SSH: `ssh -L 9000:127.0.0.1:9000 user@host`.

3. **Put TLS in front.** Session tokens travel in an `Authorization`
   header; over plain HTTP they are readable in transit. The usual
   shape is nginx or Caddy on the host terminating TLS and proxying to
   `127.0.0.1:80` and `127.0.0.1:8000`, with only 80/443 open in the
   firewall.

Also worth doing: set `DB_POOL_MAX` to 20 or lower. The default of 100
across 4 workers asks for 400 connections against Postgres's default
limit of 100.

## Reverse proxy sketch

If you terminate TLS on the host, the client and backend become
same-origin and the CORS requirement disappears:

```nginx
server {
    listen 443 ssl;
    server_name kochatim.uz;

    location / {
        proxy_pass http://127.0.0.1:80;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Two things to carry over:

- **`X-Forwarded-For` matters.** `utils/device.py:get_client_ip` reads
  it first and falls back to `remote_addr`. Without it every session
  row records the proxy's IP and the city lookup is meaningless.
- **`VITE_API_BASE_URL` must then be empty or a relative path**, and
  the client rebuilt. Note that `apiFetch` throws if `API_BASE` is
  empty, so a relative base needs a small change in `https.js`.

## Logs and operations

```bash
docker compose logs -f backend
docker compose logs -f bot
docker compose ps
```

The backend logs request timings via the admin panel's Redis counters
rather than to stdout. The bot prints `[HTTP] METHOD path -> status Nms`
for every backend call it makes through `data/database.py`, which is
the most useful signal when a flow misbehaves.

### Backups

Nothing is automated. The data lives in the `pgdata` volume:

```bash
docker compose exec -T db pg_dump -U kochatim kochatim | gzip > backup-$(date +%F).sql.gz
```

`redisdata` holds only cache, counters and the startup lock — losing it
costs the traffic history in the admin panel and nothing else.

## Volumes

| Volume | Holds | Losing it means |
|---|---|---|
| `pgdata` | All application data | Total data loss |
| `redisdata` | Cache, counters, lock | Traffic history in the admin panel |

## Running the tests on the host

The test runners are a separate Compose file and never touch the
running stack — no database, no Redis, nothing shared:

```bash
./scripts/test.sh --docker
```

Safe to run on the deployment host, though the images it pulls
(`python:3.11-slim`, `node:20-alpine`) are extra disk.
