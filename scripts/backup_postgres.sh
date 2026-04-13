#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/backend/.env"
BACKUP_DIR="${ROOT_DIR}/backups/postgres"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [ "${DB_ENGINE:-}" != "django.db.backends.postgresql" ]; then
  echo "Refusing backup: DB_ENGINE must be django.db.backends.postgresql." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT="${BACKUP_DIR}/opc-${STAMP}.dump"

PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="${DB_HOST:-127.0.0.1}" \
  --port="${DB_PORT:-5432}" \
  --username="${DB_USER:-opc}" \
  --dbname="${DB_NAME:-opc}" \
  --file="$OUTPUT"

if [ "$BACKUP_RETENTION_DAYS" -gt 0 ]; then
  find "$BACKUP_DIR" -type f -name "opc-*.dump" -mtime +"$BACKUP_RETENTION_DAYS" -delete
fi

echo "$OUTPUT"
