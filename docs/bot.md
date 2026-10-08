# Telegram Bot

aiogram **2.x** (not 3.x — the API is quite different, and a lot of
code found online will not apply). Long polling, in-memory FSM storage,
Python 3.11. It holds no database access: everything goes through the
backend's REST API with the shared `API_KEY`.

## Layout

```
bot/
  app.py            Entry point — executor.start_polling
  loader.py         Bot, Dispatcher, MemoryStorage
  api_client.py     HTTP client — users, partners, login
  data/
    config.py       Env validation, raises at import
    database.py     HTTP client — categories, types, stock, sales
  handlers/users/   One module per conversation flow
  keyboards/        Reply and inline keyboards
  states/           FSM state groups
  middlewares/      ThrottlingMiddleware
  utils/            notify_admins, set_bot_commands, rate_limit
  tests/            148 tests (123 without aiogram)
```

## There are two HTTP clients

This is the first thing to know before adding a handler.

| | `api_client.py` | `data/database.py` |
|---|---|---|
| Functions | 6 | 25 |
| Covers | `ensure_user`, `get_user`, partner accept/decline, `get_partners`, `request_login_code` | categories, types, seedlings, images, sales, plus its own `ensure_user` |
| Non-JSON response | raises the raw `ValueError` | wraps it in `BackendAPIError("... Not JSON")` |
| Logs timings | no | yes, `[HTTP] METHOD path -> status Nms` |
| Query params | not supported | `params=` supported |

Both define their own `get_session`, `_request` and `BackendAPIError`.
The two `BackendAPIError` classes are **different types** — catching
the one from `api_client` will not catch the one from `data.database`.
Import the exception from the same module as the function you called.

Both define `ensure_user`, and they are not equivalent:
`api_client.ensure_user` accepts `u_photo`, `data.database.ensure_user`
does not. `handlers/users/start.py` imports the `api_client` one
precisely because it needs to send the avatar.

Most handlers use `data.database`; only login and partners use
`api_client`. Collapsing the two into one client would be a real
improvement, but it touches every handler — until then, know which one
you are importing from.

## The shared contract both clients honour

```python
if status >= 400 or not data.get("ok"):
    raise BackendAPIError(data)
return data["data"]
```

Two things follow:

- **`ok: false` raises even on HTTP 200.** The backend can return a
  200 with `{"ok": false}`; the status code alone is not the result.
- **Only the `data` section is returned.** Handlers never see the
  envelope.

Every request carries `X-API-KEY`. That key authenticates the *bot
process*, not the gardener — the `u_id` in the body is what selects
whose data is touched. A handler that takes `u_id` from anywhere other
than `message.from_user.id` is a bug.

## `data/config.py` raises at import

```python
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi sozlanmagan! ...")
```

`BOT_TOKEN`, `API_URL`, `API_KEY` and `WEB_URL` are all required and
all raise `RuntimeError` at import time if unset. This is deliberate: a
bot that starts without a token would look healthy while doing nothing.

`ADMINS` is optional and parsed leniently — non-numeric entries are
dropped rather than raising, so one bad ID does not stop startup. Note
that `isdigit()` rejects a leading `-`, so negative (group) IDs are
silently dropped.

`API_URL` and `WEB_URL` get `.rstrip("/")`, because both clients build
URLs as `API_URL + path`. A trailing slash would produce `//api/...`.

## Handlers

One module per flow, all registered by importing them in
`handlers/users/__init__.py`. Import order is registration order, and
**`echo.py` must stay last** — it catches any unmatched message, so
anything imported after it would never receive one.

| Module | Flow |
|---|---|
| `start.py` | `/start`, profile upsert, phone gate, partner deep links |
| `contact.py` | Receives the phone number |
| `login.py` | Requests an OTP for the web dashboard |
| `cat_handler.py`, `add_cat.py` | Browse and create groups |
| `add_ty.py` | Create a variety, with an optional photo |
| `add_s.py`, `add_handler.py` | Enter stock per quality grade |
| `sale_handler.py` | Record a sale |
| `manage.py` | Rename and delete groups and varieties |
| `partners.py`, `hamkorlar.py` | Accept invites, list partners |
| `echo.py` | Fallback — keep last |

### The phone gate

`/start` upserts the user, then checks `u_phone`. Without it the bot
asks for a contact and goes no further. A partner deep link arriving
before the phone number is **stashed in FSM state** and replayed after
the contact is received — otherwise an invite would be lost to the
gate.

### Deep links

Partner invites arrive as `/start partner_<token>`. The handler reads
`message.get_args()` and strips the `partner_` prefix. The token comes
from the backend's `GET /api/partners/invite-token`, which returns the
token together with `bot_username` for building the link.

## FSM

`states/state_one.py` defines the state groups: `cat_state`,
`type_state`, `sel_state`, `img_state`, `sale_state`,
`manage_cat_state`, `manage_ty_state`, `PartnerInviteState`.

Storage is `MemoryStorage` — **state is lost on restart**. A gardener
mid-way through recording a sale when the container restarts has to
start over. Moving to `RedisStorage2` would fix it; Redis is already in
the stack.

Always `await state.finish()` at the end of a flow. A handler that
leaves the state set means every following message is swallowed by that
flow's handlers.

## Throttling

`ThrottlingMiddleware` (`middlewares/throttling.py`) applies a rate
limit per handler, with `rate_limit` (`utils/misc/throttling.py`)
setting the per-handler values:

```python
@rate_limit(5, key="start")
@dp.message_handler(CommandStart())
async def bot_start(message, state): ...
```

The decorator writes `throttling_rate_limit` and `throttling_key`
attributes onto the function; the middleware reads them back. Those two
attribute names are the contract between the files.

When throttled, the middleware replies once (twice at most) and then
goes quiet — `if throttled.exceeded_count <= 2`. That matters: a bot
that kept answering every throttled message would flood Telegram and
get rate-limited itself.

Registration is `middlewares/__init__.py`, guarded by
`if __name__ == "middlewares"` so it runs once on package import.

## Tests

148 tests in `bot/tests/`, run from `bot/pytest.ini` — a **separate
pytest root** from the backend, because `bot/utils/` and
`backend/utils/` are different packages with the same name. 25 of them
need aiogram, so a Python 3.13 host runs 123.

```bash
./scripts/test.sh bot
./scripts/test.sh --docker bot     # needed for the aiogram tests
```

Covered: both HTTP clients in full (headers, URL building, the
`ok: false` contract, the dict-unwrapping helpers, `get_cat_id` /
`get_type_id` name lookup), `data/config.py`'s import-time validation,
and the `rate_limit` / `ThrottlingMiddleware` pair.

Not covered: the handlers themselves. They are coupled to the
dispatcher and FSM storage, and testing them needs a harness that does
not exist here yet. The logic they call is covered.

Two things to know before writing a bot test:

- **aiogram 2.x will not install on Python 3.12+.** On a 3.13 host,
  `test_throttling.py` skips itself — 25 tests silently do not run.
  Use `--docker`.
- **The aiohttp session is faked at the `session.request` boundary**,
  not with `aioresponses`, which is incompatible with aiohttp 3.14.
  See `skills/testing/SKILL.md`.

## Adding a handler

1. Create the module in `handlers/users/` and import it in
   `__init__.py` — **above** `echo`.
2. Add FSM states to `states/state_one.py` if the flow has steps.
3. Call the backend through `data.database` (or `api_client` for
   users/partners/login), never a new ad-hoc `aiohttp` call.
4. Catch `BackendAPIError` **from the module you imported the function
   from** and reply with something a gardener can act on, in Uzbek.
5. `await state.finish()` on every exit path, including errors.
6. Add `@rate_limit(...)` if the handler does real work.
