#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
fi

cleanup() {
  jobs -p | xargs -r kill
}
trap cleanup EXIT

(
  cd "$ROOT_DIR/backend"
  uv sync
  uv run python manage.py migrate
  uv run python manage.py runserver 0.0.0.0:8000
) &

(
  cd "$ROOT_DIR/frontend"
  npm install
  npm run dev -- --host 0.0.0.0
) &

wait
