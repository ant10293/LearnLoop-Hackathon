#!/usr/bin/env bash
# Load the recorded demo data into the assembled app: 5 procedures with their completed learn and
# verification runs, made live against the Meta API by the author on 2026-11-02 to 2026-11-04.
#
# Downloads learnloop-demo-data.zip from this repository's GitHub release, checks its SHA-256, and
# unpacks it into build/LearnLoop/data/app. Existing data there is moved aside, never deleted.
# Set LEARNLOOP_DEMO_DATA=/path/to/learnloop-demo-data.zip to use a file you already downloaded.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/LearnLoop"
DATA="$APP/data"
URL="https://github.com/ant10293/LearnLoop-Hackathon/releases/download/demo-data-v1/learnloop-demo-data.zip"
SHA256="d53e95cfce912cb07f20c97543bfa649b97e0aff7340cd3932d766915aaf4fca"

if [[ ! -d "$APP/backend" ]]; then
  echo "LearnLoop is not assembled yet. Run scripts/setup.sh first." >&2
  exit 1
fi
for pid in $(lsof -nP -iTCP:8010 -sTCP:LISTEN -t 2>/dev/null || true); do
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1 || true)
  if [[ "$cwd" == "$APP" || "$cwd" == "$APP"/* ]]; then
    echo "LearnLoop is running from $APP. Stop scripts/run.sh first, so the database is not in use." >&2
    exit 1
  fi
done

sha256() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
ZIP="${LEARNLOOP_DEMO_DATA:-}"
if [[ -z "$ZIP" ]]; then
  ZIP="$WORK/learnloop-demo-data.zip"
  echo "Downloading demo data (about 425 MB)..."
  curl -fL --progress-bar -o "$ZIP" "$URL"
fi
if [[ "$(sha256 "$ZIP")" != "$SHA256" ]]; then
  echo "$ZIP does not have the expected SHA-256 ($SHA256). Nothing was changed." >&2
  exit 1
fi

unzip -q "$ZIP" -d "$WORK/unpacked"
if [[ ! -f "$WORK/unpacked/app/learnloop.db" ]]; then
  echo "The archive does not contain app/learnloop.db. Nothing was changed." >&2
  exit 1
fi

mkdir -p "$DATA"
if [[ -e "$DATA/app" ]]; then
  aside="$DATA/app.before-demo-$(date +%Y%m%d-%H%M%S)"
  mv "$DATA/app" "$aside"
  echo "Moved the existing data to $aside"
fi
mv "$WORK/unpacked/app" "$DATA/app"
echo "Demo data loaded into $DATA/app. Start the app with scripts/run.sh."
