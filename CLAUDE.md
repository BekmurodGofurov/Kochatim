# CLAUDE.md

The instructions for this repository live in **[AGENTS.md](AGENTS.md)**.
Read that file first; it is the single source of truth for architecture
rules, the two authentication paths, the known security issues, testing
requirements, and the git policy.

This file exists so that tools which look for `CLAUDE.md` by name find
their way there. Keep the content in `AGENTS.md` — do not duplicate
rules here, or the two will drift apart.

## Quick orientation

```
backend/   Flask REST API — the only service that touches Postgres
bot/       aiogram Telegram bot — reaches the backend over HTTP
admin/     Flask + Socket.IO monitoring panel — reads Redis only
client/    React 19 + Vite dashboard
test/      Backend test suite (admin and bot have their own roots)
docs/      Reference documentation — see the map in AGENTS.md
skills/    Task-scoped rules; load the relevant one before working
```

## Before you start

- **Writing a test?** Read `skills/testing/SKILL.md` first. This
  codebase has import-time and threading traps that will otherwise
  cost you hours.
- **Adding an endpoint?** Read `skills/backend/SKILL.md` and decide
  deliberately between `@require_api_key` (bot, service credential)
  and `@require_session` (web, user credential).
- **About to commit?** Don't, unless you were asked to in that message.

## Run the tests

```bash
./scripts/test.sh              # all four suites
./scripts/test.sh --docker     # inside the service base images
```
