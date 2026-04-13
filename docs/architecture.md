# OPC Architecture

Language: English | [Chinese](architecture.zh-CN.md)

## Product Direction

OPC (One Person Company) is a founder-facing operating desk for an OpenClaw-powered AI organization. It is not a generic technical dashboard. The user enters a business goal, and the system coordinates roles, decomposes work, executes agent turns, checks quality, and returns an executive brief.

## Tech Choice

The project follows the engineering shape of `wanny`:

| Layer | Choice | Reason |
| --- | --- | --- |
| Frontend | Vue 3 + Vite + Tailwind | Matches `wanny`, starts fast, and works well for an iterative console UI |
| Backend | Django 6 + uv | Python-friendly for OpenClaw integration, queues, model SDKs, and future orchestration |
| Local DB | SQLite | Zero-dependency MVP startup |
| Runtime | Daphne-ready ASGI | Keeps room for WebSocket mission logs and streaming activity |
| Deploy | Docker Compose | Matches the deployment style used by `wanny` |

The market research mentioned Next.js and React Flow as possible options. This scaffold intentionally starts with Vue/Django for consistency with `wanny`. If the org chart becomes more interactive, Vue Flow is the natural next addition.

## Backend API

### `GET /api/health/`

Returns basic service health.

### `GET /api/opc/briefing/`

Returns initial workspace data:

- product positioning
- OpenClaw Gateway URL
- OpenClaw Gateway health
- default OpenClaw model status
- executive team template
- execution pipeline
- MVP metrics

### `POST /api/opc/commands/`

Creates a `Mission`, starts a background OpenClaw agent turn, and returns the mission record.

Current flow:

1. Write `Mission`
2. Initialize quality gates
3. Check Gateway health
4. Check default model provider
5. Run `openclaw agent --session-id <id> --message <command> --json`
6. Store final response, raw result, token usage, and quality gate results
7. Stream mission events through WebSocket

### `GET /api/opc/missions/<mission_id>/`

Returns mission status, events, quality gates, result text, and token usage.

### `GET /api/opc/openclaw/health/`

Returns Gateway health and model provider health.

### `GET /api/opc/openclaw/logs/`

Returns recent OpenClaw Gateway logs from the CLI log reader.

### `GET /api/opc/openclaw/cost/`

Returns Gateway usage-cost data when the local Gateway pairing scope allows it. Mission-level token usage is still captured directly from `openclaw agent --json`.

## WebSocket

Mission events stream through:

```text
ws://127.0.0.1:8000/ws/missions/<mission_id>/logs/
```

Each message is a `MissionEvent` JSON object:

```json
{
  "id": 1,
  "type": "status",
  "level": "info",
  "message": "Mission succeeded.",
  "payload": {},
  "createdAt": "2026-04-13T17:40:00"
}
```

## Domain Model

- `Mission`: user command, OpenClaw session id, status, result, raw output, and token usage
- `MissionEvent`: append-only mission log and status stream
- `QualityGate`: gateway health, model provider, agent result, and cost capture checks

Future models:

- `AgentTemplate`: role name, mission, tools, model preference, and budget limit
- `Workstream`: subtask, owner agent, dependencies, and state
- `AgentRun`: runtime session, logs, token usage, cost, and result
- `BoardBrief`: final executive report with source references and recommendations

## OpenClaw Boundary

The backend keeps OpenClaw access behind `apps.desk.openclaw`. Views should not construct CLI or Gateway calls directly.

Environment boundary:

- `OPENCLAW_GATEWAY_URL`
- `OPENCLAW_GATEWAY_AUTH_MODE`
- `OPENCLAW_GATEWAY_TOKEN`
- `OPENCLAW_GATEWAY_PASSWORD`
- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

## Frontend Direction

The first screen is the working desk:

- left rail: Founder Command
- main board: Gateway/model status, org map, metrics, mission pipeline
- mission console: live events, quality gates, result text, and token usage

There is no landing page in the MVP. The product should open directly into the operational experience.

The visual direction is "boardroom operations desk": high-contrast command rail, paper-like grid surface, and restrained yellow/green/red status accents.
