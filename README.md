# OPC

Language: English | [Chinese](README.zh-CN.md)

OPC (One Person Company) is an OpenClaw-only multi-agent orchestration desk. It turns one founder command into coordinated work across a preset AI leadership team: CEO, COO, CTO, CFO, CMO, and SRE.

This repository is the MVP scaffold. Its stack follows the local `wanny` project:

- Backend: Django 6, Daphne, uv, SQLite-first
- Frontend: Vue 3, Vite, Tailwind CSS
- Deploy: Docker Compose, Nginx static frontend, Django API backend

## License And Use Restrictions

This project is released under the GNU Affero General Public License v3.0 (AGPL-3.0), as provided in `LICENSE`.

**Commercial use is not permitted without a paid license.** Personal use is free. For SaaS, enterprise, or commercial deployment, purchase a $99/yr license at: [Buy Commercial License](/docs/licensing/README.md)

See full terms and trademark disclaimer in [docs/licensing/README.md](/docs/licensing/README.md).

## Quick Start

### 1. Backend

```bash
cp .env.example .env
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

Check the API:

```bash
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/opc/briefing/
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
cp .env.example .env
docker compose up --build
```

Open http://127.0.0.1:8080.

## OpenClaw

OPC only supports OpenClaw. Deployment notes, verification commands, and maintenance commands live in [docs/openclaw-deployment.md](docs/openclaw-deployment.md).

Prepare OpenClaw and model configuration:

```bash
cp .env.example .env
# Fill AI_BASE_URL, AI_API_KEY, and AI_MODEL.
python3 scripts/bootstrap_openclaw.py
```

The script reuses an existing OpenClaw installation. If OpenClaw is missing, it installs the CLI, deploys a local Gateway, and configures the default model from `.env`.

## MVP Scope

- Founder Command: enter one executive command
- Executive Team: database-backed CEO/COO/CTO/CFO/CMO/SRE role templates
- Mission Pipeline: Intake, Decomposition, Parallel Work, Quality Gate, Board Brief
- Workstreams: persistent COO/CTO/CFO/CMO/SRE workstream records per mission
- Board Brief: persistent executive summary, recommendations, risks, and sources
- Cost/Risk: token usage, configurable cost estimate rates, quality gates, and founder approval state
- Agent Templates: create, edit, and delete role templates from the workspace UI
- Founder Approval: approve or reject pending quality gates with review notes
- Pricing Profiles: database-backed model/provider rates with pre-turn budget checks
- Mission Recovery: retry, abort, and archive mission controls
- Mission History: status/search filters and Markdown export
- Dashboard Metrics: realtime metrics stream over WebSocket
- Org Chart: Vue Flow executive graph with click-to-edit action
- Workstream Recovery: retry failed workstreams without re-running the whole mission
- Audit Log: records template edits, mission controls, approvals, and workstream retries
- Organization Scope: default local organization plus FounderProfile model for future multi-user use
- Session Auth: founder bootstrap, sign-in, sign-out, and organization-aware session API
- Strict Auth Mode: optional `OPC_REQUIRE_AUTH=true` with admin/founder/operator/viewer role checks
- PostgreSQL Path: backend driver/settings support plus migration guide
- PostgreSQL Backups: pg_dump/pg_restore helper scripts with retention cleanup
- OpenClaw Gateway: local Gateway configuration and health status
- OpenClaw Mission Adapter: backend creates missions, runs independent OpenClaw workstream agents, streams logs over WebSocket, and records token usage

## Project Structure

```text
backend/
  opc_server/     Django project
  apps/desk/           OPC API app
frontend/
  src/App.vue          OPC workspace
  src/lib/api.ts       API client
docker/                Container build and nginx config
docs/                  Product and architecture docs
scripts/dev.sh         Local dev runner
```

## Next Steps

1. Execute the per-organization template id migration before multi-tenant production use (strategy documented in `docs/template-id-strategy.md`).
2. Configure scheduled execution (cron/systemd) for PostgreSQL backup script in production deployments.
