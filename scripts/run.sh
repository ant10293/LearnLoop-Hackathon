#!/usr/bin/env bash
# Launch the assembled LearnLoop (API on 127.0.0.1:8010, app on http://127.0.0.1:5180).
# A .env in this repository's root, if present, is copied into build/LearnLoop/.env first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/LearnLoop"

if [[ ! -x "$APP/scripts/dev.sh" || ! -x "$APP/backend/.venv/bin/uvicorn" ]]; then
  echo "LearnLoop is not set up yet. Run scripts/setup.sh first." >&2
  exit 1
fi
if [[ -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env" "$APP/.env"
fi
exec "$APP/scripts/dev.sh"
