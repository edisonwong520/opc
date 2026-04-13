# OPC Backend

Language: English | [Chinese](README.zh-CN.md)

Django API for the OPC MVP. It starts with a lightweight SQLite setup so local development does not depend on MySQL or Redis.

## Local Development

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

Useful endpoints:

- `GET /api/health/`
- `GET /api/opc/briefing/`
- `POST /api/opc/commands/`
- `GET /api/opc/openclaw/health/`
- `GET /api/opc/missions/<mission_id>/`
