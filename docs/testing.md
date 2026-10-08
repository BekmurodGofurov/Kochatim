# Testing

925 tests across four suites. None of them need a database, a Redis
server, or network access.

| Suite | Root | Count | Runner |
|---|---|---|---|
| backend | `test/` | 655 | pytest |
| bot | `bot/tests/` | 148 | pytest |
| client | `client/src/**/*.test.js` | 93 | Vitest |
| admin | `admin/tests/` | 29 | pytest |

## Running them

```bash
./scripts/test.sh              # all four, one summary line each
./scripts/test.sh --docker     # inside the service base images
./scripts/test.sh backend      # one suite
./scripts/test.sh --docker bot
```

Or directly:

```bash
python -m pytest test        -c test/pytest.ini
python -m pytest admin/tests -c admin/pytest.ini
python -m pytest bot/tests   -c bot/pytest.ini
cd client && npm test
```

Local mode needs `backend/requirements.txt` plus
`test/requirements-test.txt` installed, and `npm ci` in `client/`.

### Use `--docker` for the bot

aiogram 2.x does not install on Python 3.12+. On a 3.13 host,
`bot/tests/test_throttling.py` skips itself — 25 of the 148 silently do
not run, leaving 123. The Docker runner uses `python:3.11-slim`, the same base image as
`bot/Dockerfile`, so everything executes.

That difference is not academic: running those tests in Docker for the
first time surfaced nine failures that had been invisible locally,
including two tests that were passing for the wrong reason.

## Why there are three pytest roots

`bot/utils/` and `backend/utils/` are different packages with the same
name. With both on `sys.path`, `import utils.misc.throttling` resolves
to whichever directory came first — so the bot's tests would import the
backend's `utils`. Separate roots with their own `pythonpath` keep them
apart.

## No database, no Redis

The DB layer is mocked at the pool boundary: tests patch
`db.get_conn` / `db.put_conn`, or patch `fetch_one` / `fetch_all` /
`execute` in the module under test. Nothing opens a socket.

The **cache is not mocked**. `conftest.py` installs a `fakeredis`
client over `utils.cache.redis_client`, so `get_cache` / `set_cache`
run their real code — real JSON serialisation, real TTLs, real
`SCAN` paging. Tests assert on cache state through the `redis_conn`
fixture. Mocking the cache functions would have hidden the bug that
broke the whole suite once already.

## Test structure

Three categories per unit of behaviour, as required by `AGENTS.md`:

```python
class TestSomething:
    def test_success(self): ...            # valid input, expected result
    def test_invalid_input(self): ...      # 400/404 with a code, not a 500
    def test_dependency_failure(self): ... # Postgres/Redis/HTTP raises
```

The third is the one that catches real production behaviour. Several
code paths in this repo are written to swallow failures — the cache,
the request-stats hook, `send_message`, `get_city`, the monitor loop —
and a test that asserts the request still succeeds is the only thing
pinning that contract.

## The traps

These are repo-specific and each one has cost real time. There is a
longer version with the reasoning in `skills/testing/SKILL.md`; read
that before writing a test.

### 1. Config is evaluated at import
`Config`'s class body calls `os.getenv` when the module is first
imported. Setting an env var in a fixture is too late. `conftest.py`
seeds `os.environ` at **module level**, before any backend import.

### 2. `app.py` builds the app and starts a thread at import
`app = create_app()` runs at module level, which opens a real Postgres
pool and runs `init_db()`. It also starts `system_monitor` as a daemon
thread that never stops. `conftest.py` patches `init_pool`, `init_db`
and `Thread.start` *while importing* the module.

### 3. CORS and request stats are not in `create_app()`
They are registered with `@app.before_request` / `@app.after_request`
on the module-level `app`. An app from `create_app()` has neither. The
`app` fixture returns `_app_module.app` — the same object gunicorn
serves — so the CORS policy is actually tested. `factory_app` exists
for testing the factory itself.

### 4. A star-import shadows a module name
`auth/__init__.py` does `from auth.user_id_login import *`, which binds
the **function** `user_id_login` as an attribute of the `auth` package.
`import auth.user_id_login` then gives you the function, and
`patch.object(..., "executor")` fails with
`does not have the attribute 'executor'`. Use
`sys.modules["auth.user_id_login"]`.

### 5. A thread pool outlives the patch context
`/auth/user-id-login` submits the session insert to a
`ThreadPoolExecutor` and returns immediately. The `with patch(...)`
block closes before the background job runs, so it used to connect to
the **real** Postgres during the test run. An autouse fixture replaces
that executor with one that runs inline.

### 6. `importlib.reload` defeats module-attribute patches
Reloading re-executes `from dotenv import load_dotenv`, rebinding the
name over your mock. Patch the source (`dotenv.load_dotenv`), not the
importing module's attribute.

### 7. `load_dotenv()` reads the real `.env`
With `patch.dict(os.environ, ..., clear=True)` the environment is
empty, so `load_dotenv()` happily fills it from the developer's actual
`bot/.env` — making the test depend on the machine it runs on. Patch
`load_dotenv` for those tests.

### 8. `ContextVar.get` cannot be patched
aiogram's `current_handler` is a `ContextVar`; `.get` is a read-only
C-level attribute and `mock.patch` raises
`attribute 'get' is read-only`. Use `set()` / `reset()`.

### 9. `Throttled(**kwargs)` reads non-obvious key names
aiogram's `Throttled` takes `**kwargs` and reads them under the
constants in `aiogram.dispatcher.storage`: `rate_limit` and
`exceeded`. `Throttled(rate=1, exceeded_count=3)` silently sets both
to `0`, so a test checking the `exceeded_count <= 2` branch never
exercises it. Build it with the constants.

### 10. `pubsub.listen()` blocks forever
It is a blocking generator. A test that iterates it hangs the whole
run. Use `get_message(timeout=...)`, and note that the first call with
`ignore_subscribe_messages=True` consumes the subscribe confirmation
and returns `None` — so do not break out of the poll loop on the first
`None`.

### 11. The pytest cache fails on the read-only mount
The Docker runners mount the repo `:ro`, so the runners pass
`-p no:cacheprovider`.

## What is covered

### backend (655)
Every module has tests. `test/unit/` covers the pure functions —
`security`, `time`, `errors`, `cache`, `device`, `invite_tokens`,
`images_v2`, `telegram`, `db`, `extensions`, `config`.
`test/integration/` drives every route through Flask's test client,
plus `app.py` itself: `/health`, the CORS policy, the error handlers,
the Redis counters, and one iteration of the monitor loop.

The `db.py` tests are worth knowing about — they pin the
retry-once-and-discard semantics, including that a dropped connection
goes back with `close=True` rather than being handed to the next
request.

### bot (148)
The bot has **two** HTTP clients — `api_client.py` (6 functions) and
`data/database.py` (25) — and both are covered in full: the
`X-API-KEY` header, URL and param building, the dict-unwrapping
helpers, the name-to-ID lookups, and that `{"ok": false}` raises even
on HTTP 200. Plus `data/config.py`'s import-time validation and the
`rate_limit` / `ThrottlingMiddleware` pair.

The aiohttp session is faked at the `session.request` boundary rather
than with `aioresponses`, which is incompatible with aiohttp 3.14 and
would have meant pinning the test environment away from production.

### client (93)
Vitest over the pure logic: `buildGroupsFromDashboard` (the
dashboard-to-UI transform), `toWebImgUrl` / `pickImagesFromType`, and
`apiFetch` — including that a 401 or an `UNAUTHORIZED` code clears the
stored session token.

### admin (29)
The Redis keys the panel reads are a contract with the backend that
writes them, so the tests pin the key names (`req_count:<date>`,
`endpoint_stats`). Also the week-window arithmetic, the top-10 ranking,
and that the panel renders zeroes rather than erroring when Redis is
down.

## Not covered

- **aiogram handlers** (`bot/handlers/`). They are coupled to the
  dispatcher and FSM storage; testing them needs an aiogram harness
  that does not exist here yet. The logic they call —
  `api_client`, `rate_limit` — is covered.
- **React components.** Only the pure utilities and the fetch layer are
  tested. Component tests would need `@testing-library/react`.
- **`db_init.py`.** Asserting on idempotent DDL against a mock proves
  little; it needs a real Postgres to be worth testing.
- **`client/src/api/endpoints.js`.** Dead code with a broken import —
  it imports from `./http`, which does not exist (the file is
  `https.js`), and nothing imports it. Fix or delete it before relying
  on it.
