# CEO Desk

Language: English | [Chinese](README.zh-CN.md)

CEO Desk is an OpenClaw-only multi-agent orchestration desk. It turns one executive command into coordinated work across a preset AI leadership team: CEO, COO, CTO, CFO, CMO, and SRE.

This repository is the MVP scaffold. Its stack follows the local `wanny` project:

- Backend: Django 6, Daphne, uv, SQLite-first
- Frontend: Vue 3, Vite, Tailwind CSS
- Deploy: Docker Compose, Nginx static frontend, Django API backend

## License And Use Restrictions

This project is released under the GNU Affero General Public License v3.0 (AGPL-3.0), as provided in `LICENSE`.

**Commercial use is not permitted without prior written authorization from the author.** This includes, but is not limited to, commercial SaaS, paid hosting, enterprise production use, commercial consulting delivery, closed-source product integration, resale, or sublicensing.

For commercial use, closed-source integration, private deployment licensing, or any licensing outside AGPL-3.0, contact the author for a separate commercial license.

## Quick Start

### 1. Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

Check the API:

```bash
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/desk/briefing/
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.

### 3. One-command Development

```bash
./scripts/dev.sh
```

This starts the backend on `8000` and the frontend on `5173`.

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Open http://127.0.0.1:8080.

## OpenClaw

CEO Desk only supports OpenClaw. Deployment notes, verification commands, and maintenance commands live in [docs/openclaw-deployment.md](docs/openclaw-deployment.md).

Prepare OpenClaw and model configuration:

```bash
cp .env.example .env
# Fill AI_BASE_URL, AI_API_KEY, and AI_MODEL.
python3 scripts/bootstrap_openclaw.py
```

The script reuses an existing OpenClaw installation. If OpenClaw is missing, it installs the CLI, deploys a local Gateway, and configures the default model from `.env`.

## MVP Scope

- CEO Command: enter one executive command
- Executive Team: CEO/COO/CTO/CFO/CMO/SRE role template
- Mission Pipeline: Intake, Decomposition, Parallel Work, Quality Gate, Board Brief
- Cost/Risk Placeholder: budget, quality gates, and runtime configuration placeholders
- OpenClaw Gateway: local Gateway configuration and health status
- OpenClaw Mission Adapter: backend creates missions, calls OpenClaw agents, streams logs over WebSocket, and records token usage

## Project Structure

```text
backend/
  ceo_desk_server/     Django project
  apps/desk/           CEO Desk API app
frontend/
  src/App.vue          CEO Desk workspace
  src/lib/api.ts       API client
docker/                Container build and nginx config
docs/                  Product and architecture docs
scripts/dev.sh         Local dev runner
```

## Next Steps

1. Move static executive role templates into database-backed models.
2. Add an Agent Template editor that produces OpenClaw-compatible role configuration.
3. Expand the Mission adapter from single-turn agent calls to multi-workstream orchestration.
4. Add persistent workstreams, richer execution logs, token cost estimates, and approval gates.
