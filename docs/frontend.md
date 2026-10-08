# Frontend

React 19 + Vite 6, SCSS (no CSS framework), `react-router-dom` 7,
`recharts` for charts, `lucide-react` for icons. Built to static files
and served by nginx.

## Layout

```
client/src/
  App.jsx               Routes
  main.jsx              Entry
  api/
    https.js            API_BASE + apiFetch — the only HTTP layer
    endpoints.js        Dead code, broken import (see below)
  auth/RequireAuth.jsx  Route guard
  components/           One folder per component: .jsx + .scss
  context/
    DashboardContext.jsx
    ThemeContext.jsx
  pages/                dashboard, inventory, sales, settings, login, home, gardener
  utils/
    buildGroups.js      Dashboard response → UI shape
    imageUtils.js       Image URL resolution
  style/                global.scss, variables.scss
```

## `apiFetch` — the whole HTTP layer

`src/api/https.js`. Every call goes through it; there is no axios
instance despite axios being in `package.json`.

```js
export const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
```

Vite inlines `import.meta.env` at **build** time. Changing
`VITE_API_BASE_URL` needs a rebuild, not a restart — and in Docker it
arrives as a build arg (`PUBLIC_URL` in the root `.env`), not an
environment variable on the running container.

Four behaviours worth knowing:

1. **The session token comes from `localStorage`** under
   `session_token` and is sent as `Authorization: Bearer <token>`. If
   there is no token the header is omitted entirely rather than sent
   empty.
2. **`ok: false` throws even on HTTP 200.** The backend can return 200
   with `{"ok": false}`, so the status code alone is not the result.
   On success only `data.data` is returned — callers never see the
   envelope.
3. **A 401 or an `UNAUTHORIZED` code clears the stored token.** That is
   what makes an expired session fall back to the login page instead
   of retrying forever. Other errors leave the token alone, so a 500
   does not log the user out.
4. **`FormData` skips the `Content-Type` header** so the browser can
   set `multipart/form-data` with its own boundary, and the body is
   passed through rather than `JSON.stringify`-ed. Setting the header
   manually here produces a request the backend cannot parse.

The thrown error carries `status`, `code` and `payload`, so a caller
can branch on `err.code === "INSUFFICIENT_STOCK"` rather than matching
on message text.

### `endpoints.js` is dead code

It does `import { apiFetch } from "./http"` — there is no `http.js`,
the file is `https.js` — and nothing imports it. It would fail to
resolve if anything did. Fix the import or delete the file; do not
build on it.

## Auth flow

`RequireAuth` checks for `session_token` in `localStorage` and
redirects to `/login` when absent. That is a **UX guard, not
security** — every protected route's data comes from a
`@require_session` endpoint that validates the token server-side.
Deleting the guard would expose no data.

`TelegramHandler` runs outside the router guard and handles the Mini
App path: it reads `window.Telegram.WebApp.initData` and posts it to
`/auth/telegram-webapp` to exchange it for a session token.

Public routes: `/`, `/login`, `/gardeners/:uId`. Everything else is
behind `RequireAuth` and `AppLayout` (sidebar + content).

Note that `/gardeners/:uId` is public on the client **and** its backing
endpoint (`GET /api/users/<u_id>/dashboard`) is public on the server —
which is issue 4 in `security.md`, since that endpoint returns
`u_phone`.

## `buildGroupsFromDashboard`

`src/utils/buildGroups.js`. `GET /api/me/dashboard` returns three flat
lists — `categories`, `types`, `seedlings` — and this joins them into
the nested shape the UI renders:

```js
[{ id, groupName, totalValue, sorts: [{ id, t_id, name, nav1, nav2, nav3,
                                       images, description,
                                       updated_at, added_at }], groupImages }]
```

Three rules that are easy to break:

- **A variety with no `seedlings` row still appears, at zero.** The
  seedling map is a lookup with a `{q1: 0, q2: 0, q3: 0}` default, not
  a filter. Turning it into a join would make a newly added variety
  vanish from the dashboard until stock was entered.
- **IDs are compared as numbers.** `Number(t.c_id) === c_id`, because
  the API can return either `1` or `"1"` depending on the path. A `===`
  on raw values would drop varieties.
- **`description` probes four field names** — `deff`, `description`,
  `t_desc`, `t_deff`. The column is `deff`; the rest are historical.

`totalValue` is the sum of all three grades across every variety in the
group, coerced with `|| 0` so a null never produces `NaN`.

## Images

`src/utils/imageUtils.js`.

```js
toWebImgUrl(raw)   // https URL → unchanged; anything else → /api/img/<encoded>
pickImagesFromType(t)  // → [url] or []
```

`img.i_url` can hold either an ImgBB `https://` URL **or** a bare
Telegram `file_id`, depending on whether conversion succeeded when the
row was written. `toWebImgUrl` handles both: a URL passes through, and
a `file_id` is routed through the backend's public proxy. The
`encodeURIComponent` is load-bearing — `file_id`s can contain `/`.

`pickImagesFromType` probes `i_url`, `image`, `image_url`, `t_image`,
`img`, `photo`, `photo_url` and returns at most one image in an array.
`i_url` is the field the backend actually sends; the rest are
historical.

## State

Two contexts, no Redux or Zustand.

- **`DashboardContext`** holds the dashboard response and is what lets
  pages share it without refetching. The backend already caches it for
  60s, so this is mostly about avoiding a flash of loading state on
  navigation.
- **`ThemeContext`** holds light/dark, persisted to `localStorage`.

Most pages read one endpoint and reshape it client-side rather than
calling several. `GET /api/me/dashboard` and `GET /api/me/settings` are
both deliberately bundled server-side for that reason.

## Styling

Per-component SCSS next to the `.jsx` (`Sidebar.jsx` +
`Sidebar.scss`), with `style/variables.scss` for shared tokens and
`style/global.scss` for resets. Dark mode comes from `ThemeContext`
setting an attribute the SCSS keys off.

## Build and serve

```bash
npm ci
npm run dev        # port 5174, strictPort — see vite.config.js
npm run build      # → dist/
npm test           # Vitest
```

Docker is a two-stage build: `node:20-alpine` runs `npm run build` with
`VITE_API_BASE_URL` as a build arg, then `nginx:1.27-alpine` serves
`dist/`.

`nginx.conf` is an SPA fallback — `try_files $uri $uri/ /index.html` —
so client-side routes work on a hard refresh. It does **not** proxy the
API: the browser talks to the backend directly on port 8000, which is
why `ALLOWED_ORIGINS` has to list the client's origin.

If you ever add an `/api` proxy to nginx, the CORS requirement
disappears, but `VITE_API_BASE_URL` has to become a relative path.

## Tests

93 Vitest tests, config in `vitest.config.js` (separate from
`vite.config.js`, which keeps the dev-server settings).

```bash
cd client && npm test
./scripts/test.sh client
```

Covered: `buildGroupsFromDashboard` in full, `toWebImgUrl` /
`pickImagesFromType`, and `apiFetch` — request building, the Bearer
header, the `FormData` path, the `ok: false` contract, and the
token-clearing behaviour on 401.

Not covered: components. That would need
`@testing-library/react`, which is not installed. `environment: "jsdom"`
is already configured, so adding it is the only missing step.

`VITE_API_BASE_URL` is set in `vitest.config.js` under `test.env` —
without it `API_BASE` is empty and `apiFetch` throws before doing
anything.
