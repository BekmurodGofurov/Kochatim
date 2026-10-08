# Deployment

One host, one Docker Compose file, six containers. There is no load
balancer, no orchestrator, and no staging environment —
`docker-compose.yml` is the entire topology.

## Containers

nginx runs on the **host**, not in Docker, and owns ports 80 and 443.
Docker publishes nothing to the internet.

| Service | Image | Published port | Notes |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `127.0.0.1:5432` | Loopback only |
| `redis` | `redis:7-alpine` | none | Docker network only |
| `backend` | built from `backend/` | `127.0.0.1:8000` | gunicorn, 4 workers. Not public — the host's nginx fronts it. |
| `admin` | built from `admin/` | `127.0.0.1:9000` | **No authentication.** Loopback only; reach it over SSH. |
| `bot` | built from `bot/` | none | Outbound long polling only |
| `client` | built from `client/` | `8080` (profile `local`) | Not started in production — the frontend is on Cloudflare Pages |

All on the `kochatim` bridge network, where services address each other
by name: `db`, `redis`, `backend`.

Only **80 and 443** should be open in the firewall or security group.

## Production topology

The frontend is built and served by Cloudflare Pages; the server runs
the API, the bot and the data stores.

```
browser ──https──► Cloudflare Pages                (kochatim.uz — static files)
   │
   └────https────► api.kochatim.uz
                   (A → server IP, DNS only)
                          │
                   host nginx :443  ──http──►  127.0.0.1:8000  (backend container)
```

**The API must be HTTPS.** Pages serves the frontend over HTTPS, and a
page served over HTTPS cannot call an `http://` API — the browser
blocks it as mixed content. That is the whole reason nginx is in front.

nginx is installed on the host with apt, outside Docker. Docker binds
the backend to `127.0.0.1:8000`, so the only way in from the internet
is through nginx.

### Why the Cloudflare record stays grey

certbot renews over the Let's Encrypt HTTP-01 challenge, which arrives
on port 80 at the origin. With the orange cloud on, Cloudflare answers
that challenge instead and renewal starts failing — silently, about two
months later when the first renewal is due.

So: leave `api.kochatim.uz` on **DNS only**, and keep port 80 open. It
is not only for the initial issue; the systemd timer needs it every
~60 days.

If you do want the orange cloud, set the SSL/TLS mode to
**Full (strict)** and switch certbot to the DNS-01 challenge with a
Cloudflare API token. Do not use **Flexible** — it leaves the
Cloudflare-to-origin hop as plain HTTP, and session tokens travel in an
`Authorization` header over that hop.

### First deploy

```bash
# 1. DNS: api.kochatim.uz  A  <server-ip>   (DNS only / grey cloud)
# 2. Firewall / security group: allow 80 and 443 only

# 3. Application
docker compose up -d --build
curl -s localhost:8000/health        # backend up on loopback?

# 4. nginx + TLS
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp deploy/nginx/api.kochatim.uz.conf \
        /etc/nginx/sites-available/api.kochatim.uz
sudo ln -s /etc/nginx/sites-available/api.kochatim.uz \
           /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d api.kochatim.uz

# 5. Verify
curl -I https://api.kochatim.uz/health
systemctl list-timers | grep certbot     # renewal timer installed?
```

`certbot --nginx` edits the site file in place: it adds the
`listen 443 ssl` block, the certificate paths and a redirect from port
80, and installs a systemd timer that renews automatically. After it
runs, copy the result back into `deploy/nginx/` so the repo stays the
source of truth.

Dry-run the renewal once, so you find out now rather than in two
months:

```bash
sudo certbot renew --dry-run
```

### Settings that must line up

| Where | Setting | Value |
|---|---|---|
| `backend/.env` | `ALLOWED_ORIGINS` | `https://kochatim.uz,https://www.kochatim.uz` |
| Cloudflare Pages → Settings → Environment variables | `VITE_API_BASE_URL` | `https://api.kochatim.uz` |
| Cloudflare Pages | `VITE_TG_BOT_USERNAME` | your bot's username |
| `bot/.env` | `WEB_URL` | `https://kochatim.uz` |
| `bot/.env` | `API_URL` | `http://backend:8000` — internal, stays HTTP |

Two of these bite if you get them wrong:

- **`ALLOWED_ORIGINS` takes exact origins**, scheme included, no
  trailing slash, and an empty value rejects everything. A mismatch
  shows in the browser as `Access-Control-Allow-Origin: null` — that
  is the backend refusing the origin, not a bug.
- **`VITE_API_BASE_URL` is inlined at build time.** Setting it in Pages
  requires a **redeploy** to take effect; it is not read at runtime.

`API_URL` for the bot deliberately stays plain HTTP: the bot talks to
the backend over the Docker network, inside the host, so routing it
back out through nginx and the public internet would add latency and a
TLS handshake for nothing.

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
curl -s https://api.kochatim.uz/health
```

The backend creates and migrates its own schema on start
(`db_init.py`), so there is no migration step. Four gunicorn workers
would race, so one wins a Redis lock and the rest skip — see
`database.md`.

### The frontend is built, not configured

`VITE_API_BASE_URL` is inlined into the JavaScript at build time, so it
is a build input everywhere — never runtime config.

**In production** it is a Cloudflare Pages environment variable.
Changing it needs a **redeploy** of the Pages project; saving the
variable alone does nothing.

**Locally**, the `client` container takes it as a build arg from
`PUBLIC_URL`:

```bash
docker compose --profile local up -d --build client
```

Restarting the container is not enough. This is the most common
deployment mistake here.

## Before exposing this to the internet

Two of the four items here are now handled by `docker-compose.yml`:
`admin` and `backend` are bound to `127.0.0.1`, and nginx terminates
TLS. The other two are still open. Detail and fixes in `security.md`.

1. **`POST /auth/user-id-login` still issues sessions without
   authentication.** It returns a valid 30-day token for any `u_id`
   that exists — no password, no OTP, no signature. A firewall cannot
   mitigate it: the endpoint is public by design, and that design is
   the problem. The fix is to delete the route; the OTP and Telegram
   Mini App login paths already cover every real case.

2. **`GET /api/gardeners` and `GET /api/users/<u_id>/dashboard` are
   public and return `u_phone`.** Together they let anyone enumerate
   every gardener's Telegram ID and phone number — and that Telegram
   ID is exactly what makes item 1 exploitable at scale.

Already dealt with:

- ~~Do not publish port 9000~~ — `admin` is on `127.0.0.1:9000`. Reach
  it with `ssh -L 9000:127.0.0.1:9000 admin@<server>`.
- ~~Put TLS in front~~ — host nginx + certbot, renewed by a systemd
  timer.
- `DB_POOL_MAX` is 20 in `backend/.env.example`, not the old 100.
  Check the value in your actual `backend/.env`: 4 workers × 100 asks
  for 400 connections against Postgres's default limit of 100.

## The reverse proxy

`deploy/nginx/api.kochatim.uz.conf`, installed to
`/etc/nginx/sites-available/` on the host. Four things in it matter:

- **`client_max_body_size 10m`.** nginx defaults to 1m, which rejects
  most phone photos with a 413 before the request reaches Flask —
  `POST /api/img/upload` would fail for no visible reason.
- **`X-Forwarded-For`.** `utils/device.py:get_client_ip` reads it first
  and falls back to `remote_addr`. Without it every session row records
  the proxy's address and the city lookup is meaningless.
- **No `add_header Access-Control-*`.** Flask already sends the CORS
  headers from `ALLOWED_ORIGINS`. A second set makes the browser see
  two values and reject the response outright — which looks exactly
  like a CORS misconfiguration and sends you hunting in the wrong file.
- **`proxy_buffering off` for `/api/img/`.** That route streams image
  bytes proxied from Telegram; buffering a binary body in memory buys
  nothing.

certbot owns the `listen 443` block. Keep the repo copy in sync after
any certbot change, or the next person deploying will install a config
that silently differs from what is running.

To serve the frontend from this server too, rather than Pages, add a
second server block for `kochatim.uz` and start the client container
under the `local` profile. Then `VITE_API_BASE_URL` can become a
relative path and the CORS requirement disappears — though `apiFetch`
currently throws on an empty `API_BASE`, so that needs a small change
in `https.js` first.

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
