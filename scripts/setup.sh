#!/usr/bin/env bash
# One-command setup: assemble LearnLoop from the pinned dependency plus the overlay, then install
# backend and frontend dependencies inside build/LearnLoop.
#
#   scripts/setup.sh
#
# Options (environment variables):
#   PYTHON=python3.12              Python 3.12+ interpreter for the backend (auto-detected)
#   LEARNLOOP_SKIP_PERCEPTION=1    skip torch and the DINOv2 weights (appearance checks then
#                                  report themselves unavailable; nothing else changes)
#   LEARNLOOP_E2E=1                also install the Playwright Chromium browser for e2e tests
#   VTB_SOURCE=<url or path>       fetch vision-test-bench from somewhere other than GitHub
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/LearnLoop"
cd "$ROOT"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required tool: $1. $2" >&2; exit 1; }; }
need git "Install Git."
need node "Install Node.js 20 or newer."
need npm "Install npm (comes with Node.js)."
node -e 'process.exit(parseInt(process.versions.node) >= 20 ? 0 : 1)' \
  || { echo "Node.js 20 or newer is required (found $(node --version))." >&2; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || echo "Warning: ffmpeg was not found. LearnLoop needs it to ingest videos." >&2

if [[ -z "${PYTHON:-}" ]]; then
  for candidate in python3.12 python3.13 python3.14 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  done
fi
[[ -n "${PYTHON:-}" ]] || { echo "Python 3.12 or newer is required. Set PYTHON=/path/to/python3.12." >&2; exit 1; }

echo "== 1/4 Assemble LearnLoop"
"$PYTHON" scripts/assemble.py ${VTB_SOURCE:+--dependency "$VTB_SOURCE"}

echo "== 2/4 Backend environment ($("$PYTHON" --version))"
if [[ ! -x "$APP/backend/.venv/bin/python" ]]; then
  "$PYTHON" -m venv "$APP/backend/.venv"
fi
EXTRAS="dev,perception"
[[ "${LEARNLOOP_SKIP_PERCEPTION:-0}" == "1" ]] && EXTRAS="dev"
"$APP/backend/.venv/bin/python" -m pip install --quiet --upgrade pip
"$APP/backend/.venv/bin/python" -m pip install --quiet -e "$APP/backend[$EXTRAS]"
if [[ "$EXTRAS" == *perception* ]]; then
  echo "   Loading DINOv2 ViT-S/14 weights (Meta, one-time download)"
  (cd "$APP/backend" && .venv/bin/python -m app.perception.encoder) \
    || echo "Warning: DINOv2 weights could not be loaded now; the first analysis will try again." >&2
fi

echo "== 3/4 Frontend dependencies"
npm ci --prefix "$APP/frontend" --no-audit --no-fund --loglevel=error
if [[ "${LEARNLOOP_E2E:-0}" == "1" ]]; then
  (cd "$APP/frontend" && npx playwright install chromium)
fi

echo "== 4/4 Done"
echo "Start LearnLoop:  scripts/run.sh   (then open http://127.0.0.1:5180)"
echo "Run the tests:    scripts/verify.sh"
