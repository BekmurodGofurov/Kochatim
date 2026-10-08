# Admin Monitoring Panel

A small Flask + Socket.IO app on port 9000 that shows live CPU/RAM, a
live request feed, and daily/weekly request counts. It reads **Redis
only** — it never connects to Postgres.

> **It has no authentication.** Anything that can reach port 9000 reads
> the traffic profile. Bind it to loopback and put auth on it — see
> `security.md`.

## Files

```
admin/
  app.py              Everything — 80 lines
  templates/index.html
  static/script.js    Socket.IO client, charts
  static/style.css
  tests/              29 tests
```

## The Redis contract

The panel does not talk to the backend. The two communicate entirely
through Redis keys, which makes those key names a contract between the
services. Change one on either side and the panel silently shows
nothing.

| Key | Type | Written by | Read by |
|---|---|---|---|
| `req_count:<YYYY-MM-DD>` | string counter, 8-day TTL | `backend/app.py:_record_endpoint_stats` | `request_counts()` |
| `endpoint_stats` | sorted set, path → count | same | `get_stats()` |
| `server_metrics` | pub/sub channel | `backend/app.py:system_monitor` | `redis_listener()` |
| `live_requests` | pub/sub channel | `backend/app.py:_record_endpoint_stats` | `redis_listener()` |

`admin/tests/test_admin_app.py` asserts these names literally, so a
rename on either side breaks a test rather than the panel in
production.

## Routes

| Method | Path | Returns |
|---|---|---|
| GET | `/` | The dashboard page |
| GET | `/api/stats` | `{logs: {today: {total}, this_week: {total}}, endpoints: [{path, count}]}` |

### `request_counts()`

Builds the list of dates from Monday to today, `MGET`s all of them, and
sums. `this_week` is the sum; `today` is the last element.

The whole thing is wrapped in `try/except`, returning zeroes if Redis
is unavailable — the panel should still render. A non-numeric value in
a counter also lands in that handler and yields zero.

### `get_stats()`

Top 10 endpoints by count:

```python
redis_client.zrevrangebyscore("endpoint_stats", "+inf", "-inf",
                              withscores=True, start=0, num=10)
```

Scores come back as floats, so counts are cast with `int()` before
serialising — otherwise the JSON would carry `5.0` instead of `5`.

`endpoint_stats` has **no TTL**, so it accumulates since the first
deploy. The daily counters expire after 8 days; the ranking does not.
Worth knowing when reading the numbers: the ranking is all-time, not
this week.

## WebSocket

```python
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")
```

A daemon thread (`redis_listener`) subscribes to both channels and
re-emits each message as a Socket.IO event:

| Redis channel | Socket.IO event |
|---|---|
| `server_metrics` | `metrics` |
| `live_requests` | `live_request` |

Each message is parsed inside a `try/except` so one malformed payload
cannot kill the listener. That matters more than it looks: the listener
is a daemon thread, and if it dies the panel just goes quiet with no
error anywhere.

`cors_allowed_origins="*"` is wide open. Combined with no
authentication, that is the second half of issue 2 in `security.md` —
locking down the HTTP routes without also restricting the socket
leaves the live feed readable.

`decode_responses=True` on the Redis client is load-bearing: without
it `json.loads` receives bytes and the channel comparison
(`channel == 'server_metrics'`) fails against `b'server_metrics'`.
There is a test for it.

## Serving

```dockerfile
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "-w", "1", "-b", "0.0.0.0:9000", "app:app"]
```

Two details that are easy to break:

- **One worker.** Each worker would run its own `redis_listener`
  thread, and each would emit to only its own connected clients.
- **The gevent-websocket worker, not plain gunicorn.** It
  monkey-patches the process *before* the app module is imported,
  which is what makes the blocking `pubsub.listen()` loop cooperate
  with the event loop. Running `socketio.run(..., async_mode="gevent")`
  directly hits the blocking-call problem the Dockerfile comment
  mentions.

## Tests

29 tests, `admin/pytest.ini`:

```bash
./scripts/test.sh admin
```

`admin/app.py` does three things at import that the tests have to stop:
it builds `SocketIO(async_mode='gevent')` (which needs gevent
installed), creates a real Redis client, and starts the listener
thread. `admin/tests/conftest.py` patches `SocketIO`, swaps in
`fakeredis`, and neutralises `Thread.start`, then calls
`redis_listener()` directly with a fake pubsub that yields a finite
list of messages.

Covered: the week-window arithmetic, the top-10 ranking and its int
cast, the Redis key names, every `except` branch (Redis down,
non-numeric counter, malformed pub/sub payload), and
`decode_responses`.

`test_needs_no_auth` records that `/api/stats` is open. When you fix
that, invert the test.
