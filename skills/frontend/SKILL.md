---
name: kochatim-frontend
description: Rules for Kochatim's React client. Use whenever writing or editing anything under client/ — a component, a page, an API call, or styling. Covers apiFetch as the only HTTP layer (and why ok:false throws on HTTP 200), that import.meta.env is inlined at build time so changing the API URL needs a rebuild, the dashboard-to-UI transform and its zero-stock rule, image URL resolution for Telegram file_ids, and that endpoints.js is dead code with a broken import.
---

# Kochatim Frontend Rules

React 19, Vite 6, SCSS, `react-router-dom` 7, `recharts`,
`lucide-react`. No CSS framework, no state library beyond two contexts.

## All HTTP goes through `apiFetch`

`src/api/https.js`. Never call `fetch` directly, and do not add an
axios instance — axios is in `package.json` but unused, and a second
HTTP layer would duplicate the auth and error handling.

```js
import { apiFetch } from "../api/https";

const data = await apiFetch("/api/me/dashboard");
await apiFetch("/api/categories/me", { method: "POST", body: { c_name } });
```

What it already does for you:

- Sends `Authorization: Bearer <token>` from `localStorage` when a
  token exists, and omits the header entirely when it does not.
- **Throws when `ok: false`, even on HTTP 200.** The backend returns
  `{ok: false}` with a 200 in places, so the status code alone is not
  the result.
- Returns `data.data` on success — callers never see the envelope.
- **Clears the stored token on a 401 or an `UNAUTHORIZED` code**, which
  is what makes an expired session fall through to the login page.
  Other errors leave it alone, so a 500 does not log the user out.
- Skips `Content-Type` for `FormData` so the browser sets the
  boundary.

### Branch on `err.code`, not on the message

```js
try {
  await apiFetch("/api/seedlings/update", { method: "POST", body });
} catch (err) {
  if (err.code === "INSUFFICIENT_STOCK") {
    setError("Omborda yetarli ko'chat yo'q.");
  } else {
    setError(err.message);
  }
}
```

The error carries `status`, `code` and `payload`. Messages are in Uzbek
and get reworded; codes are the stable contract.

### Do not import `endpoints.js`

`src/api/endpoints.js` does `import { apiFetch } from "./http"` — there
is no `http.js`, the file is `https.js` — and nothing imports it. It
would fail to resolve. Fix the import or delete the file; do not build
on it.

## `import.meta.env` is inlined at build time

```js
export const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
```

Vite substitutes these at **build** time, not runtime. Consequences:

- Changing `VITE_API_BASE_URL` needs `npm run build`, or
  `docker compose up -d --build client`. Restarting the container does
  nothing. This is the most common deployment mistake in this repo.
- In Docker the value arrives as a **build arg** (`PUBLIC_URL` in the
  root `.env`), not an environment variable on the container.
- `apiFetch` throws when `API_BASE` is empty, so a missing
  `client/.env` fails loudly rather than silently calling the wrong
  host.

Any new `VITE_*` variable goes in `client/.env.example` and, if it
needs to reach the Docker build, in `docker-compose.yml`'s `args`.

## The backend is a different origin

nginx serves the static files and does **not** proxy the API — the
browser calls port 8000 directly. So every origin the client runs on
must be listed in the backend's `ALLOWED_ORIGINS`, including
`http://localhost:5174` for `npm run dev`.

A CORS failure shows as `Access-Control-Allow-Origin: null`. That is
the backend rejecting the origin, not a bug in the request.

## Prefer the bundled endpoints

The backend deliberately bundles two responses so a page needs one
call, not five:

- `GET /api/me/dashboard` — user, categories, types, seedlings, sales
  summary
- `GET /api/me/settings` — partners, sessions, invite token, bot
  username

Read those and reshape client-side rather than adding parallel calls.
`DashboardContext` holds the dashboard response so pages share it
without refetching.

## `buildGroupsFromDashboard`

`src/utils/buildGroups.js` joins the three flat lists into the nested
shape the UI renders. Three rules that are easy to break:

- **A variety with no `seedlings` row must still appear, at zero.** The
  seedling lookup has a `{q1: 0, q2: 0, q3: 0}` default; it is not a
  filter. Turning it into a join would make a newly added variety
  vanish from the dashboard until stock was entered.
- **Compare IDs as numbers.** `Number(t.c_id) === c_id` — the API
  returns `1` or `"1"` depending on the path, and a `===` on raw values
  silently drops rows.
- **`description` probes four field names** — `deff`, `description`,
  `t_desc`, `t_deff`. The column is `deff`; the rest are historical.
  Keep the fallbacks.

Coerce with `|| 0` when summing, so a null never produces `NaN` in a
total.

## Images: two possible values in one field

`img.i_url` holds either an ImgBB `https://` URL **or** a bare Telegram
`file_id`, depending on whether conversion succeeded when the row was
written. Always go through the helper:

```js
import { pickImagesFromType, toWebImgUrl } from "../utils/imageUtils";

<img src={toWebImgUrl(sort.images[0])} alt={sort.name} />
```

`toWebImgUrl` passes a URL through and routes anything else to the
backend's public proxy, `encodeURIComponent`-ed — `file_id`s can
contain `/`, which would otherwise break the path. Never interpolate
`i_url` into a `src` yourself.

`pickImagesFromType` probes seven field names and returns at most one
image in an array.

## Auth is a UX guard, not security

`RequireAuth` checks for `session_token` in `localStorage` and
redirects to `/login`. The actual enforcement is server-side on every
`@require_session` endpoint — deleting the guard would expose no data,
only show empty pages.

So: do not put anything secret in the client, and do not assume a
component is unreachable because it is behind the guard.

`TelegramHandler` runs outside the guard and handles the Mini App path,
exchanging `window.Telegram.WebApp.initData` for a session token.

## Structure and styling

- One folder per component, `.jsx` + `.scss` beside each other.
- Shared tokens in `style/variables.scss`, resets in
  `style/global.scss`.
- Dark mode comes from `ThemeContext`; key off the attribute it sets
  rather than duplicating a theme check in JS.
- Pages go in `pages/`, reusable pieces in `components/`.

## Before you finish

Add Vitest tests for any new pure function or API wrapper
(`client/src/**/*.test.js`):

```bash
cd client && npm test
```

`VITE_API_BASE_URL` is set in `vitest.config.js` under `test.env`.
`API_BASE` is read at module load, so asserting against the imported
`API_BASE` is more robust than a hardcoded string. Mock
`globalThis.fetch` and clear `localStorage` between tests — see
`skills/testing/SKILL.md`.

Component tests would need `@testing-library/react`, which is not
installed; `jsdom` already is.

Update `docs/frontend.md` if you add a route or change the data flow.
