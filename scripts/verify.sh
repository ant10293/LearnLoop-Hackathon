#!/usr/bin/env bash
# Check the assembled application: provenance match, backend tests, frontend type check and
# production build, and frontend tests. Set LEARNLOOP_E2E=1 to also run the Playwright smoke test
# (needs `LEARNLOOP_E2E=1 scripts/setup.sh` once for the browser).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/LearnLoop"
[[ -x "$APP/backend/.venv/bin/python" ]] || { echo "Run scripts/setup.sh first." >&2; exit 1; }
PY="$APP/backend/.venv/bin/python"

echo "== Byte-for-byte comparison with LearnLoop at the audited commit"
"$PY" "$ROOT/scripts/compare_with_learnloop.py"

echo "== Backend tests"
(cd "$APP/backend" && .venv/bin/python -m pytest -q)

echo "== Frontend type check and production build"
npm --prefix "$APP/frontend" run build

echo "== Frontend tests"
npm --prefix "$APP/frontend" test

if [[ "${LEARNLOOP_E2E:-0}" == "1" ]]; then
  echo "== Browser end-to-end smoke test"
  (cd "$APP/frontend" && npx playwright test)
fi
echo "All checks passed."
