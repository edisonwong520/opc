#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/restore_postgres.sh <backup.dump>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/backend/.env"
BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [ "${DB_ENGINE:-}" != "django.db.backends.postgresql" ]; then
  echo "Refusing restore: DB_ENGINE must be django.db.backends.postgresql." >&2
  exit 1
fi

PGPASSWORD="${DB_PASSWORD:-}" pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --host="${DB_HOST:-127.0.0.1}" \
  --port="${DB_PORT:-5432}" \
  --username="${DB_USER:-opc}" \
  --dbname="${DB_NAME:-opc}" \
  "$BACKUP_FILE"
