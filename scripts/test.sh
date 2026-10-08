#!/usr/bin/env bash
#
# Runs every suite in the repo and prints one summary line per service.
#
#   ./scripts/test.sh              # local interpreters
#   ./scripts/test.sh --docker     # inside the service base images
#   ./scripts/test.sh backend      # one suite only
#   ./scripts/test.sh --docker bot
#
# Local mode needs a Python env with backend/requirements.txt and
# test/requirements-test.txt installed, and `npm ci` in client/.
# It skips the bot's aiogram tests on Python 3.13, which aiogram 2.x
# does not support — use --docker to run those.
set -uo pipefail

cd "$(dirname "$0")/.."

DOCKER=0
SUITES=()

for arg in "$@"; do
  case "$arg" in
    --docker) DOCKER=1 ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    backend|admin|bot|client) SUITES+=("$arg") ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [ ${#SUITES[@]} -eq 0 ]; then
  SUITES=(backend admin bot client)
fi

# Local mode picks up the repo's venv if there is one, else `python3`.
PY="python3"
for candidate in backend/.venv/bin/python .venv/bin/python; do
  if [ -x "$candidate" ]; then PY="$candidate"; break; fi
done

declare -a NAMES=() RESULTS=()
OVERALL=0

run() {
  local name="$1"; shift
  echo ""
  echo "──────────── $name ────────────"
  if "$@"; then
    NAMES+=("$name"); RESULTS+=("pass")
  else
    NAMES+=("$name"); RESULTS+=("FAIL")
    OVERALL=1
  fi
}

compose_run() {
  docker compose -f docker-compose.test.yml run --rm "$1"
}

for suite in "${SUITES[@]}"; do
  if [ "$DOCKER" -eq 1 ]; then
    run "$suite" compose_run "test-$suite"
    continue
  fi

  case "$suite" in
    backend) run backend "$PY" -m pytest test -c test/pytest.ini ;;
    admin)   run admin   "$PY" -m pytest admin/tests -c admin/pytest.ini ;;
    bot)     run bot     "$PY" -m pytest bot/tests -c bot/pytest.ini ;;
    client)  run client  sh -c 'cd client && npm test' ;;
  esac
done

echo ""
echo "════════════ summary ════════════"
for i in "${!NAMES[@]}"; do
  printf '  %-9s %s\n' "${NAMES[$i]}" "${RESULTS[$i]}"
done

exit "$OVERALL"
