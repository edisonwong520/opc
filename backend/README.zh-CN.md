# CEO Desk Backend

语言：[English](README.md) | 中文

CEO Desk MVP 的 Django API。默认使用轻量 SQLite，本地开发不依赖 MySQL 或 Redis。

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
- `GET /api/desk/briefing/`
- `POST /api/desk/commands/`
- `GET /api/desk/openclaw/health/`
- `GET /api/desk/missions/<mission_id>/`
