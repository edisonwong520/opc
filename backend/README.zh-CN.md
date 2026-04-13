# OPC Backend

语言：[English](README.md) | 中文

OPC MVP 的 Django API。默认使用轻量 SQLite，本地开发不依赖 MySQL 或 Redis。

## 本地开发

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

常用 endpoints：

- `GET /api/health/`
- `GET /api/opc/briefing/`
- `POST /api/opc/commands/`
- `GET /api/opc/openclaw/health/`
- `GET /api/opc/missions/<mission_id>/`
