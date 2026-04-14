# OPC Backend

Language: English | [Chinese](README.zh-CN.md)

Django API backend for OPC (One Person Company) multi-agent orchestration desk. Built with Django 6, Daphne/ASGI, and Channels for WebSocket support.

## Environment Configuration

The backend reads environment variables from the **project root `.env`** file (parent directory). Do not create a `.env` inside the `backend/` directory.

```bash
# From project root
cp .env.example .env
# Edit .env with your configuration
```

Key environment variables:

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | Enable debug mode (true/false) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `DB_ENGINE` | Database engine (sqlite3 or postgresql) |
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway WebSocket URL |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw Gateway auth token |
| `AI_BASE_URL` | OpenAI-compatible API base URL |
| `AI_API_KEY` | AI API key |
| `AI_MODEL` | Model identifier |
| `OPC_REQUIRE_AUTH` | Require authentication (true/false) |

## Local Development

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

For WebSocket support via Daphne:

```bash
uv run daphne -b 0.0.0.0 -p 8000 opc_server.asgi:application
```

## Testing

```bash
uv run pytest
```

## API Endpoints

All endpoints are under `/api/opc/`:

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/opc/auth/me/` | Current user info |
| POST | `/api/opc/auth/login/` | Sign in |
| POST | `/api/opc/auth/logout/` | Sign out |
| POST | `/api/opc/auth/bootstrap/` | Bootstrap founder account |

### Missions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/opc/commands/` | Create mission from command |
| GET | `/api/opc/missions/` | List missions (with filters) |
| GET | `/api/opc/missions/<id>/` | Mission detail |
| POST | `/api/opc/missions/<id>/approve/` | Approve mission |
| POST | `/api/opc/missions/<id>/reject/` | Reject mission |
| POST | `/api/opc/missions/<id>/retry/` | Retry failed workstreams |
| POST | `/api/opc/missions/<id>/abort/` | Abort running mission |
| POST | `/api/opc/missions/<id>/archive/` | Archive mission |
| GET | `/api/opc/missions/<id>/export/` | Export mission as Markdown |
| POST | `/api/opc/missions/<id>/workstreams/<ws_id>/retry/` | Retry specific workstream |

### Agent Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/opc/templates/` | Create template |
| PATCH | `/api/opc/templates/<id>/` | Update template |

### OpenClaw Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/opc/openclaw/health/` | Gateway health status |
| GET | `/api/opc/openclaw/logs/` | Recent Gateway logs |
| GET | `/api/opc/openclaw/cost/` | Token usage and cost |

### Audit & Invitations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/opc/audit-logs/` | Browse audit records |
| GET | `/api/opc/invitations/` | List invitations |
| POST | `/api/opc/invitations/create/` | Create invitation |
| POST | `/api/opc/invitations/<token>/accept/` | Accept invitation |
| POST | `/api/opc/invitations/<id>/revoke/` | Revoke invitation |

### Misc

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/opc/briefing/` | Dashboard briefing |
| GET | `/api/health/` | API health check |

## WebSocket

Metrics stream available at `/ws/metrics/`:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics/');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## PostgreSQL Migration

For production, switch from SQLite to PostgreSQL:

1. Update `.env`:
   ```bash
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=opc
   DB_USER=opc
   DB_PASSWORD=your-password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   ```

2. Run migrations:
   ```bash
   uv run python manage.py migrate
   ```

3. Use backup scripts:
   ```bash
   scripts/backup_postgres.sh
   scripts/restore_postgres.sh
   ```

## Project Structure

```
backend/
├── opc_server/        # Django project config
│   ├── settings.py    # Environment-loaded settings
│   ├── urls.py        # Root URL routing
│   ├── asgi.py        # ASGI application
│   └── wsgi.py        # WSGI application
├── apps/
│   └── desk/          # OPC API app
│       ├── models.py  # Mission, Workstream, Template, etc.
│       ├── views.py   # API endpoints
│       ├── urls.py    # App URL routing
│       ├── openclaw/  # OpenClaw integration service
│       └── tests/     # pytest tests
├── pyproject.toml     # uv package config
└── README.md
```

## Dependencies

- Django 6.0+
- Daphne 4.2+ (ASGI server)
- Channels 4.3+ (WebSocket)
- django-cors-headers
- psycopg (PostgreSQL driver)
- python-dotenv