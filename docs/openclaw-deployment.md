# OpenClaw Deployment

Language: English | [Chinese](openclaw-deployment.zh-CN.md)

OPC only supports OpenClaw. It does not support any other agent runtime.

This document records the local OpenClaw deployment baseline for OPC.

## Current Deployment

| Item | Value |
| --- | --- |
| OpenClaw CLI | `2026.4.11` |
| Node.js | `v24.11.1` |
| Gateway mode | `local` |
| Gateway bind | `loopback` |
| Gateway port | `7788` |
| Gateway URL | `ws://127.0.0.1:7788` |
| Dashboard URL | `http://127.0.0.1:7788/` |
| Auth mode | `token` |
| macOS service | `~/Library/LaunchAgents/ai.openclaw.gateway.plist` |
| OpenClaw config | `~/.openclaw/openclaw.json` |
| Workspace | `~/.openclaw/workspace` |
| Logs | `~/.openclaw/logs/gateway.log` and `/tmp/openclaw/openclaw-YYYY-MM-DD.log` |

The Gateway is installed as a macOS LaunchAgent and has been verified with `openclaw gateway status`:

- service loaded
- runtime running
- listening on `127.0.0.1:7788`
- RPC probe OK after warm-up

## Official References

- Installation: https://openclawdoc.com/docs/getting-started/installation/
- CLI Gateway help: https://docs.openclaw.ai/cli/gateway
- CLI Onboard help: https://docs.openclaw.ai/cli/onboard
- Troubleshooting: https://docs.openclaw.ai/troubleshooting

## Install Commands

The current machine already has Node.js 24. OpenClaw requires Node.js 22+ and recommends Node.js 24.

```bash
node -v
npm -v
npm install -g openclaw@latest
openclaw --version
```

Deploy the Gateway:

```bash
TOKEN="$(openssl rand -hex 24)"

openclaw onboard \
  --non-interactive \
  --accept-risk \
  --mode local \
  --auth-choice skip \
  --gateway-bind loopback \
  --gateway-port 7788 \
  --gateway-auth token \
  --gateway-token "$TOKEN" \
  --install-daemon \
  --skip-channels \
  --skip-ui \
  --skip-search \
  --skip-skills \
  --json
```

Notes:

- `--auth-choice skip` deploys the Gateway without configuring a model provider during onboarding.
- `--gateway-bind loopback` keeps access local to the machine.
- `--gateway-auth token` protects the Gateway. The token stays in local OpenClaw config and is never committed.
- `--skip-channels` skips Telegram, Discord, WhatsApp, and similar channels. OPC only needs the Gateway.

## Verify

```bash
openclaw gateway status
openclaw health
openclaw doctor
```

Expected:

- `openclaw gateway status` shows `Runtime: running`
- `RPC probe: ok`
- `Listening: 127.0.0.1:7788`

Current non-blocking `doctor` notes:

- The Gateway service uses Node from nvm. If Node is upgraded later, reinstall the Gateway service.
- The bundled Discord voice dependency is not installed. Discord channels are not enabled, so this does not affect OPC.

## Service Commands

```bash
openclaw gateway status
openclaw gateway restart
openclaw gateway stop
openclaw gateway start
openclaw logs
```

## OPC Configuration

The backend points to OpenClaw Gateway through `OPENCLAW_GATEWAY_URL`:

```bash
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:7788
OPENCLAW_GATEWAY_AUTH_MODE=token
OPENCLAW_GATEWAY_TOKEN=<local-token>
OPENCLAW_GATEWAY_PASSWORD=
```

The current Gateway uses token auth and has no password. For `http://localhost:7788/chat?session=main`, use `gateway.auth.token` from `~/.openclaw/openclaw.json`.

To avoid manual copying, sync the token into the local project `.env` files:

```bash
python3 scripts/sync_openclaw_env.py
```

The script writes:

- `.env`
- `backend/.env`

Both files are ignored by Git and must not be committed.

## Model Configuration

OpenClaw model configuration follows the `wanny` backend `.env` convention and uses an OpenAI-compatible triple:

```bash
AI_BASE_URL=https://api.deepseek.com/v1
AI_API_KEY=sk-your-ai-key-here
AI_MODEL=deepseek-chat
```

On this development machine, the bootstrap script can fill missing values from `/Users/edison/code/python/wanny/backend/.env`.

The script configures OpenClaw as:

- provider id: `opc`
- default model: `opc/<AI_MODEL>`
- API adapter: `openai-completions`

Recommended user flow:

```bash
python3 scripts/bootstrap_openclaw.py
```

Script behavior:

- If OpenClaw CLI is missing, it runs `npm install -g openclaw@latest`.
- If `~/.openclaw/openclaw.json` is missing, it deploys a local OpenClaw Gateway.
- If OpenClaw already exists, it does not redeploy. It only syncs Gateway auth and model configuration.
- If `wanny/backend/.env` exists and this project `.env` is missing `AI_*`, it fills the missing model settings.
- It syncs Gateway token into `.env` and `backend/.env`.
- It writes `AI_*` into local OpenClaw config for the launchd Gateway service.
- It sets the OpenClaw default model to `opc/<AI_MODEL>`.

Verify the model:

```bash
openclaw models status --json
openclaw models list --provider opc
```

Model API keys are stored in local OpenClaw config and local `.env` files. Do not copy `.env`, `backend/.env`, or `~/.openclaw` secrets into docs, issues, or commits.

## OPC OpenClaw Integration

The integration is implemented as:

1. Gateway health probe: `GET /api/opc/openclaw/health/`
2. Token handling: local `.env` and `backend/.env`, both ignored by Git
3. Mission adapter: `POST /api/opc/commands/` creates a Mission and calls `openclaw agent`
4. Streaming logs: `ws://<host>/ws/missions/<mission_id>/logs/`
5. Cost and quality gates: Mission records token usage and gateway/model/result/cost gates

## OPC OpenClaw API

### Health

```bash
curl http://127.0.0.1:8000/api/opc/openclaw/health/
```

Returns:

- whether the Gateway service is running
- whether RPC probe is OK
- whether pairing is required for management RPCs
- whether the default model provider is usable

### Create Mission

```bash
curl -X POST http://127.0.0.1:8000/api/opc/commands/ \
  -H 'Content-Type: application/json' \
  -d '{"command":"Reply exactly: integration-ok"}'
```

Backend behavior:

1. Create `Mission`
2. Initialize quality gates
3. Run `openclaw agent --session-id <id> --message <command> --json` in the background
4. Write `MissionEvent` records
5. Capture OpenClaw final response and token usage

### Mission Detail

```bash
curl http://127.0.0.1:8000/api/opc/missions/<mission_id>/
```

Returns mission status, result, events, quality gates, and token usage.

### Streaming Logs

The frontend connects to:

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

### Cost

```bash
curl http://127.0.0.1:8000/api/opc/openclaw/cost/?days=30
```

OpenClaw Gateway `usage-cost` may be degraded when the local Gateway pairing scope rejects management RPCs. Mission-level token usage is still captured from `openclaw agent --json` via `agentMeta.usage`.

## Reinstall Or Repair

Reinstall the service:

```bash
openclaw gateway stop
openclaw gateway install
openclaw gateway start
openclaw gateway status
```

Run automatic repair:

```bash
openclaw doctor --fix
```

Run `doctor --fix` only when you need Discord voice dependencies or Node runtime migration. The MVP does not require it.
