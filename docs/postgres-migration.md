# PostgreSQL Migration Path

OPC defaults to SQLite for local development. PostgreSQL is the production migration target.

## Runtime Support

The backend includes `psycopg[binary]` and accepts PostgreSQL through Django settings:

```bash
DB_ENGINE=django.db.backends.postgresql
DB_NAME=opc
DB_USER=opc
DB_PASSWORD=replace-with-local-password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=60
```

## Local Migration Steps

1. Create a PostgreSQL database and user.

```bash
createdb opc
createuser opc
```

2. Update `backend/.env` with the PostgreSQL settings above.

3. Run migrations.

```bash
cd backend
uv run python manage.py migrate
```

4. Create a Django admin user if needed.

```bash
uv run python manage.py createsuperuser
```

5. Start the backend and verify OpenClaw health.

```bash
uv run python manage.py runserver 0.0.0.0:8000
curl http://127.0.0.1:8000/api/opc/openclaw/health/
```

## Data Migration From SQLite

For a local SQLite database that should be preserved:

```bash
cd backend
DB_ENGINE=django.db.backends.sqlite3 uv run python manage.py dumpdata \
  --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.Permission \
  > opc-sqlite-export.json

# Switch backend/.env to PostgreSQL, then:
uv run python manage.py migrate
uv run python manage.py loaddata opc-sqlite-export.json
```

Review `AgentTemplate`, `Mission`, `PricingProfile`, and `AuditLog` records after import. The migration `0008` assigns legacy rows to the `default` organization.

## Production Notes

- Use a managed PostgreSQL service or a dedicated local PostgreSQL instance.
- Keep database credentials in `.env` or the deployment secret store.
- Back up PostgreSQL before applying migrations.
- Do not run long OpenClaw mission traffic during a data migration.

## Backup And Restore Scripts

Create a custom-format PostgreSQL backup:

```bash
scripts/backup_postgres.sh
```

Backups are written to `backups/postgres/`, which is ignored by Git. The script deletes `opc-*.dump` files older than `BACKUP_RETENTION_DAYS`; the default retention is 14 days. Set `BACKUP_RETENTION_DAYS=0` to disable cleanup.

Restore a backup into the configured PostgreSQL database:

```bash
scripts/restore_postgres.sh backups/postgres/opc-YYYYMMDD-HHMMSS.dump
```

The restore script uses `pg_restore --clean --if-exists`; run it only against a database you intend to replace.
