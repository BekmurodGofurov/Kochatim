---
name: kochatim-bot
description: Rules for Kochatim's aiogram Telegram bot. Use whenever writing or editing anything under bot/ — a handler, a keyboard, an FSM flow, or an API call. Covers the two separate HTTP clients and which to import from (their BackendAPIError classes are different types), aiogram 2.x vs 3.x, handler registration order and why echo must stay last, FSM cleanup, the phone gate, rate limiting, and that data/config.py raises at import.
---

# Kochatim Bot Rules

aiogram **2.x**, long polling, in-memory FSM, Python 3.11. The bot
holds no database access — everything goes through the backend's REST
API.

## This is aiogram 2.x, not 3.x

The APIs differ substantially and most aiogram material online targets
3.x. In 2.x:

- Handlers register with `@dp.message_handler(...)`, not a `Router`.
- `FSMContext` is injected as a handler argument.
- Filters come from `aiogram.dispatcher.filters`.
- Middleware subclasses `BaseMiddleware` with `on_process_message`.

`bot/requirements.txt` pins `aiogram~=2.14`. **It will not install on
Python 3.12+** — which is why the Dockerfile uses `python:3.11-slim`
and why bot tests need `./scripts/test.sh --docker` on a newer host.

## There are two HTTP clients — know which you are importing

| | `api_client.py` | `data/database.py` |
|---|---|---|
| Covers | users, partners, login codes | categories, types, seedlings, images, sales |
| Functions | 6 | 25 |
| Non-JSON response | raises raw `ValueError` | raises `BackendAPIError("... Not JSON")` |
| `params=` support | no | yes |
| Logs timings | no | yes |

Both define their own `get_session`, `_request` and `BackendAPIError`.

> **The two `BackendAPIError` classes are different types.** Catching
> the one from `api_client` will not catch the one from
> `data.database`. Import the exception from the same module as the
> function you called.

```python
from data.database import new_cat, BackendAPIError      # consistent
from api_client import request_login_code, BackendAPIError  # also fine
```

Both also define `ensure_user`, and they differ:
`api_client.ensure_user` takes `u_photo`, `data.database.ensure_user`
does not. `start.py` imports the `api_client` one because it sends the
avatar.

Use `data.database` for catalogue, stock and sales; `api_client` for
login and partners. **Never add a third client or a bare `aiohttp`
call** — route new calls through whichever of the two already covers
that area.

## The response contract

Both clients do the same thing:

```python
if status >= 400 or not data.get("ok"):
    raise BackendAPIError(data)
return data["data"]
```

So a handler receives the `data` section directly, and **`ok: false`
raises even on HTTP 200** — the status code alone is not the result.

Every request carries `X-API-KEY`, which authenticates the *bot
process*, not the gardener. The `u_id` in the body selects whose data
is touched, so it must always come from `message.from_user.id`:

```python
u = message.from_user
await ensure_user(u_id=u.id, u_name=u.full_name, u_username=u.username)
```

Taking `u_id` from message text or state would let one gardener act as
another.

## Handler registration order

Handlers register by being imported in `handlers/users/__init__.py`,
and import order is registration order.

> **`echo` must stay last.** It catches any unmatched message, so
> anything imported after it never receives one.

Add new modules above it.

## Always finish the FSM state

```python
@dp.message_handler(state=sale_state.price)
async def sale_price(message: types.Message, state: FSMContext):
    try:
        await add_sale(...)
    except BackendAPIError as e:
        await message.answer("Sotuvni saqlab bo'lmadi. Qayta urinib ko'ring.")
        await state.finish()      # also on the error path
        return
    await message.answer("Saqlandi ✅")
    await state.finish()
```

A handler that leaves the state set means every following message is
swallowed by that flow — the gardener appears to have a dead bot.
Finish on **every** exit path, errors included.

Storage is `MemoryStorage`, so **state is lost on restart**. Do not put
anything in FSM state that matters beyond the current conversation.

## The phone gate

`/start` upserts the user and then checks `u_phone`. Without it the bot
asks for a contact and goes no further. Any new entry point has to
respect that, and anything arriving before the phone number must be
**stashed in state and replayed** — that is what `start.py` does with
partner deep links, so an invite is not lost to the gate.

Deep links arrive as `/start partner_<token>`; read them with
`message.get_args()`.

## Rate limiting

```python
from utils.misc.throttling import rate_limit

@rate_limit(5, key="start")
@dp.message_handler(CommandStart())
async def bot_start(message, state): ...
```

`rate_limit` writes `throttling_rate_limit` and `throttling_key` onto
the function; `ThrottlingMiddleware` reads them back. Those attribute
names are the contract between the two files — if you rename one,
rename both.

Add it to any handler that does real work (an API call, a photo
download). The middleware replies at most twice and then goes quiet, so
a flooding user does not make the bot flood Telegram in return.

## `data/config.py` raises at import

`BOT_TOKEN`, `API_URL`, `API_KEY` and `WEB_URL` all raise
`RuntimeError` at import if unset. Keep that — a bot running without a
token looks healthy while doing nothing.

Import settings from `data.config`, never `os.getenv` directly in a
handler, so the validation applies. `API_URL` and `WEB_URL` are already
`rstrip("/")`-ed; do not add a slash when building a URL.

## Error messages are for gardeners

The audience is Uzbek-speaking nursery owners, not developers. Never
show a raw `BackendAPIError`:

```python
except BackendAPIError:
    await message.answer("Hozir saqlab bo'lmadi. Birozdan keyin urinib ko'ring.")
```

Branch on the backend's `code` when the user can act on it —
`INSUFFICIENT_STOCK` deserves "you only have N" rather than a generic
failure.

## Keyboards can send whole objects back

`keyboards/` builds reply and inline keyboards, and several of them
round-trip a whole row. That is why `data.database`'s helpers accept a
dict as well as a value:

```python
async def get_cat_id(u_id, c_name):
    if isinstance(c_name, dict):
        ...
```

and why the backend's `api/types.py:_to_int` does the same. If you add
a helper that takes an ID from a keyboard callback, tolerate both
shapes or normalise at the boundary.

Name lookups (`get_cat_id`, `get_type_id`) are case- and
whitespace-insensitive and return `None` when not found — check for
`None` rather than assuming a hit.

## Before you finish

Add tests to `bot/tests/` for any new client function: success, the
`ok: false` path, and the request wiring (method, URL, params, body).
Fake the aiohttp session at the `session.request` boundary with the
`backend` / `db_backend` fixtures — **read
`skills/testing/SKILL.md`**, especially the aiogram-specific traps
(`ContextVar.get` cannot be patched; `Throttled`'s kwargs are not the
names they look like).

Run them in Docker:

```bash
./scripts/test.sh --docker bot
```

Update `docs/bot.md` if you add a flow or change registration order.
