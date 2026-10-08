---
name: kochatim-testing
description: Use whenever writing, fixing, or running a test in the Kochatim repo — a backend endpoint test, a util test, a bot test, an admin test, or a client Vitest test. AGENTS.md requires every new endpoint and util to ship with a success test, an invalid-input test, and a dependency-failure test; this skill covers what those three need to check and the eleven repo-specific traps that will otherwise cost hours: config is read at import time, app.py builds the app and starts a thread at module level, CORS is registered outside the factory, a star-import shadows a module name, a thread pool escapes the patch context, and aiogram will not install on Python 3.13.
---

# Kochatim Testing Rules

925 tests, four suites, no database and no Redis server. Read the traps
below before writing one — most of them fail in a way that does not
point at the cause.

## Running them

```bash
./scripts/test.sh              # all four
./scripts/test.sh --docker     # inside the service base images
./scripts/test.sh backend      # one suite
```

| Suite | Root | Config |
|---|---|---|
| backend | `test/` | `test/pytest.ini` |
| bot | `bot/tests/` | `bot/pytest.ini` |
| admin | `admin/tests/` | `admin/pytest.ini` |
| client | `client/src/**/*.test.js` | `client/vitest.config.js` |

**Three pytest roots, not one.** `bot/utils/` and `backend/utils/` are
different packages with the same name; with both on `sys.path`,
`import utils.misc.throttling` resolves to whichever came first. Do not
consolidate them.

## The three tests every endpoint needs

1. **Success** — a valid, representative call. Assert the status, the
   `ok` field, and the shape of `data`.
2. **Invalid input** — missing field, wrong type, out-of-range value.
   Assert a 400/404 **with a `code`**, never an unhandled 500.
3. **Dependency failure** — mock the DB call or the external HTTP call
   to raise. Assert a clean error.

The third is the one that earns its keep here, because a lot of this
codebase deliberately swallows failures: `utils/cache.py`,
`_record_endpoint_stats`, `send_message`, `get_city`, and
`system_monitor` all catch and continue. For those, the assertion is
that **the user's request still succeeds**:

```python
def test_redis_failure_does_not_break_the_request(self, client):
    with patch("utils.cache.redis_client.zincrby",
               side_effect=redis.ConnectionError("down")):
        assert client.get("/health").status_code == 200
```

Without a test like that, someone later "fixes" the bare `except` and
turns a Redis blip into a site outage.

For a session route, also assert **the unauthenticated case returns
401** and that the query is scoped by `g.u_id` — taking `u_id` from the
request body on a session route is an IDOR, and a test is the cheapest
place to catch it.

## Mock the database, use the real cache

**Database: mocked.** Patch the names *in the module under test*,
because handlers do `from db import fetch_one`:

```python
with patch("api.categories.fetch_all", return_value=[FAKE_CATEGORY]):
    resp = client.get("/api/categories", headers=SESSION_H)
```

For `db.py`'s own tests, patch at the pool boundary — `db.get_conn`
and `db.put_conn`.

**Cache: not mocked.** `conftest.py` installs a `fakeredis` client over
`utils.cache.redis_client`, so `get_cache` / `set_cache` run their real
code with real JSON serialisation and real TTLs. Assert on cache state
through the `redis_conn` fixture:

```python
def test_dashboard_is_cached(self, client, mock_session, redis_conn):
    ...
    assert redis_conn.exists(f"dashboard_{TEST_U_ID}")
```

This is deliberate. The whole suite was once dead because `conftest`
cleared `utils.cache._store`, a dict that stopped existing when the
cache moved to Redis — and because the cache functions were mocked
everywhere, nothing noticed for a long time.

## Useful fixtures

| Fixture | Gives you |
|---|---|
| `client` | Flask test client on the module-level app |
| `app` | The module-level `app` object (see trap 3) |
| `factory_app` | A fresh `create_app()` result, for testing the factory |
| `app_module` | The `backend/app.py` module, for `_cors_origin`, `system_monitor` |
| `redis_conn` | The fakeredis instance |
| `mock_session` | Passes `require_session`, cache-hit path, sets `g.u_id` |
| `mock_session_miss` | Passes it via the DB path, exercising `set_cache` |
| `mock_no_session` | Rejects it — neither cache nor DB has the session |
| `api_key_headers` / `session_headers` / `no_auth_headers` | Header dicts |

Bot suite: `api_client`, `backend`, `database`, `db_backend` — the last
two for `data/database.py`, which is a second HTTP client.

---

# The eleven traps

## 1. `Config` is evaluated at import

`Config`'s attributes are class-body assignments, so `os.getenv` runs
when the module is first imported. **A fixture is too late.**
`conftest.py` seeds `os.environ` at module level, before any backend
import. If you need a different value, either patch the attribute
(`patch("utils.invite_tokens.Config.API_KEY", "x")`) or
`importlib.reload` the module.

## 2. `app.py` builds the app and starts a thread at import

`app = create_app()` runs at module level — opening a real Postgres
pool and running `init_db()` — and `system_monitor` starts as a daemon
thread that never stops. `conftest.py` imports the module inside:

```python
with patch("extensions.init_pool"), patch("db_init.init_db"), \
     patch.object(threading.Thread, "start", lambda self: None):
    import app as app_module
```

Importing `app` without those three needs a live database and leaves a
thread publishing to Redis for the rest of the run.

## 3. CORS and request stats are not in `create_app()`

They are registered with `@app.before_request` / `@app.after_request`
on the **module-level** `app`. An app from `create_app()` has neither,
so a test using it silently asserts nothing about CORS.

The `app` fixture returns `_app_module.app` — the same object gunicorn
serves. Use `factory_app` only to test the factory itself.

## 4. A star-import shadows a module name

`auth/__init__.py` does `from auth.user_id_login import *`, binding the
**function** `user_id_login` as an attribute of the `auth` package. So
`import auth.user_id_login as m` gives you the function, and
`patch.object(m, "executor")` fails with
`does not have the attribute 'executor'`.

```python
_uidl = sys.modules["auth.user_id_login"]   # the module
```

## 5. A thread pool outlives the patch context

`/auth/user-id-login` submits the session insert to a
`ThreadPoolExecutor` and returns immediately, so the `with patch(...)`
block closes before the background job runs — and it then connects to
the **real** Postgres. That is what produced
`Background session insertion failed: role "test" does not exist` in
test output.

An autouse fixture (`inline_background_executor`) swaps in an executor
that runs inline. Leave it alone; if you add another background
dispatch, add it there too.

## 6. `importlib.reload` defeats module-attribute patches

Reloading re-executes the module body, so `from dotenv import
load_dotenv` rebinds the name over your mock. Patch the **source**:

```python
with patch("dotenv.load_dotenv"):          # works
with patch("data.config.load_dotenv"):     # silently undone by reload
    importlib.reload(config_module)
```

## 7. `load_dotenv()` reads the developer's real `.env`

With `patch.dict(os.environ, {...}, clear=True)` the environment is
empty, so `load_dotenv()` fills it from the actual `bot/.env` on disk —
making the test depend on the machine. Patch `load_dotenv` for any test
that clears the environment.

## 8. `ContextVar.get` cannot be patched

aiogram's `current_handler` is a `ContextVar`; `.get` is a read-only
C-level attribute and `mock.patch` raises
`attribute 'get' is read-only`. Use the real API:

```python
token = current_handler.set(handler)
try:
    ...
finally:
    current_handler.reset(token)
```

## 9. `Throttled(**kwargs)` reads non-obvious key names

aiogram's `Throttled` takes `**kwargs` and reads them under the
constants in `aiogram.dispatcher.storage` — `rate_limit` and
`exceeded`, **not** `rate` and `exceeded_count`. So
`Throttled(rate=1, exceeded_count=3)` sets both to `0` and the test
passes for the wrong reason: the `exceeded_count <= 2` branch is never
exercised. Build it with the constants:

```python
from aiogram.dispatcher.storage import EXCEEDED_COUNT, KEY, RATE_LIMIT
Throttled(**{KEY: "k", RATE_LIMIT: 1, EXCEEDED_COUNT: 3})
```

This is the general shape of the risk: a kwarg a constructor quietly
ignores makes a test green without testing anything.

## 10. `pubsub.listen()` blocks forever

It is a blocking generator — a test that iterates it hangs the whole
run. Use `get_message(timeout=...)`, and note that the first call with
`ignore_subscribe_messages=True` consumes the subscribe confirmation
and returns `None`, so **do not break out of the poll loop on the
first `None`**:

```python
def drain(pubsub, polls=10):
    out = []
    for _ in range(polls):
        msg = pubsub.get_message(timeout=0.05)
        if msg is not None and msg.get("type") == "message":
            out.append(msg)
    return out
```

For the admin panel's `redis_listener`, which iterates `listen()`
itself, inject a fake pubsub whose `listen()` returns a **finite**
iterator.

## 11. aiogram will not install on Python 3.12+

On a 3.13 host, `bot/tests/test_throttling.py` skips itself via
`pytest.importorskip("aiogram")` and 25 of the bot suite's 148 tests
silently do not run. Use `--docker`, which runs `python:3.11-slim`.

Note that the skip has to be at the **top of the file**, before
`from utils.misc.throttling import rate_limit`: `bot/utils/__init__.py`
imports `notify_admins`, which imports aiogram, so even the pure-Python
helper cannot be imported without it.

Related: the Docker runners mount the repo read-only, so they pass
`-p no:cacheprovider`.

---

## Writing a bot test

`data/database.py` and `api_client.py` are **two separate HTTP
clients** with their own `get_session`, `_request` and
`BackendAPIError`. The two exception classes are different types.
Import from the module you are testing.

Fake the aiohttp session at the `session.request` boundary, not with
`aioresponses` — it is incompatible with aiohttp 3.14, and pinning
aiohttp down for tests would mean testing against a different library
than production runs:

```python
async def test_sends_api_key(self, api_client, backend):
    backend.respond(payload={"ok": True, "data": {"u_id": 1}})
    await api_client.get_user(1)
    assert backend.last["headers"]["X-API-KEY"] == TEST_API_KEY
```

`FakeSession.request` returns an object that is its own async context
manager, which is what `async with session.request(...)` needs.

## Writing an admin test

`admin/app.py` does three things at import: builds
`SocketIO(async_mode='gevent')` (needs gevent installed), creates a
real Redis client, and starts the listener thread. `conftest.py`
patches `SocketIO`, swaps in fakeredis, and neutralises
`Thread.start`.

The Redis key names (`req_count:<date>`, `endpoint_stats`,
`server_metrics`, `live_requests`) are a **contract with the backend**
that writes them. Assert them literally, so a rename on either side
breaks a test instead of the panel.

## Writing a client test

Vitest, `jsdom`, config in `client/vitest.config.js` — separate from
`vite.config.js`, which holds the dev-server settings.

`VITE_API_BASE_URL` is set under `test.env`. Without it `API_BASE` is
empty and `apiFetch` throws before doing anything.

`API_BASE` is read at module load from `import.meta.env`, so it cannot
be changed per-test without `vi.resetModules()` and a dynamic import.
Assert against the imported `API_BASE` rather than a hardcoded string.

Mock `globalThis.fetch` and clear `localStorage` between tests:

```js
beforeEach(() => { localStorage.clear(); });
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });
```

## Conventions

- Group with `class TestSomething:` and name tests as sentences —
  `test_expired_token_is_rejected`, not `test_token_2`.
- Shared fakes go in `conftest.py` (`FAKE_USER`, `FAKE_CATEGORY`, …).
  Do not redefine them per file.
- Comment **why** a test exists when it is pinning a non-obvious
  contract. `test_discarded_connection_is_never_reused` says what
  breaks if the behaviour changes; that comment is the valuable part.
- Assert on `error.code`, not on message text. Messages are in Uzbek
  and get reworded.
- `pytest.mark.parametrize` for table cases — UA strings, env
  variants, rejection codes.
- Never write a test that needs network access, a real database, or a
  real Redis. If you reach for one, the fixture you need already
  exists.
