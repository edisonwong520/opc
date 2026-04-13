# Development Guide

## Requirements

- Python 3.12+
- uv
- Node.js 22+
- npm
- Docker Desktop, optional

## Backend Commands

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

Run tests:

```bash
cd backend
uv run pytest
```

## Frontend Commands

```bash
cd frontend
npm install
npm run dev
npm run build
```

## Environment

Backend environment lives in `backend/.env`.

Important variables:

- `DJANGO_DEBUG`: `true` for local development
- `DJANGO_ALLOWED_HOSTS`: comma-separated host allowlist
- `DJANGO_CORS_ALLOWED_ORIGINS`: frontend dev origins
- `OPENCLAW_GATEWAY_URL`: OpenClaw gateway endpoint

Frontend environment:

- `VITE_API_BASE_URL`: optional API base URL for production builds

During local Vite development, `/api` is proxied to `http://127.0.0.1:8000`.

## Coding Notes

- Keep agent orchestration behind backend service modules rather than calling runtimes from views directly.
- Keep templates data-driven. The initial hardcoded team in `apps.desk.views` is only an MVP seed.
- Add persistence before wiring real long-running agent tasks.
- Treat cost tracking and quality gates as first-class product surfaces, not afterthoughts.
