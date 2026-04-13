# OpenClaw 部署

语言：[English](openclaw-deployment.md) | 中文

CEO Desk 只支持 OpenClaw，不支持 NanoClaw 或其他 agent runtime。

本文记录 CEO Desk 的本机 OpenClaw 部署基线。

## 当前部署

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

Gateway 已安装为 macOS LaunchAgent，并通过 `openclaw gateway status` 验证：

- service loaded
- runtime running
- listening on `127.0.0.1:7788`
- warm-up 后 RPC probe OK

## 官方参考

- Installation: https://openclawdoc.com/docs/getting-started/installation/
- CLI Gateway help: https://docs.openclaw.ai/cli/gateway
- CLI Onboard help: https://docs.openclaw.ai/cli/onboard
- Troubleshooting: https://docs.openclaw.ai/troubleshooting

## 安装命令

当前机器已有 Node.js 24。OpenClaw 要求 Node.js 22+，推荐 Node.js 24。

```bash
node -v
npm -v
npm install -g openclaw@latest
openclaw --version
```

部署 Gateway：

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

说明：

- `--auth-choice skip` 只部署 Gateway，不在 onboard 阶段配置模型 provider。
- `--gateway-bind loopback` 只允许本机访问。
- `--gateway-auth token` 会保护 Gateway。token 只保存在本机 OpenClaw 配置中，不提交。
- `--skip-channels` 跳过 Telegram、Discord、WhatsApp 等 channel。CEO Desk 当前只需要 Gateway。

## 验证

```bash
openclaw gateway status
openclaw health
openclaw doctor
```

预期：

- `openclaw gateway status` 显示 `Runtime: running`
- `RPC probe: ok`
- `Listening: 127.0.0.1:7788`

当前非阻断提醒：

- Gateway service 使用 nvm 下的 Node。未来升级 Node 后，可能需要重新安装 Gateway service。
- bundled Discord voice dependency 未安装。当前未启用 Discord channel，不影响 CEO Desk。

## 服务命令

```bash
openclaw gateway status
openclaw gateway restart
openclaw gateway stop
openclaw gateway start
openclaw logs
```

## CEO Desk 配置

后端通过 `OPENCLAW_GATEWAY_URL` 指向 OpenClaw Gateway：

```bash
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:7788
OPENCLAW_GATEWAY_AUTH_MODE=token
OPENCLAW_GATEWAY_TOKEN=<local-token>
OPENCLAW_GATEWAY_PASSWORD=
```

当前 Gateway 使用 token auth，没有 password。访问 `http://localhost:7788/chat?session=main` 时，使用 `~/.openclaw/openclaw.json` 中的 `gateway.auth.token`。

同步 token：

```bash
python3 scripts/sync_openclaw_env.py
```

脚本写入：

- `.env`
- `backend/.env`

这两个文件被 Git 忽略，不应提交。

## 模型配置

OpenClaw 模型配置参考 `wanny` 的后端 `.env` 约定，使用 OpenAI-compatible 三元组：

```bash
AI_BASE_URL=https://api.deepseek.com/v1
AI_API_KEY=sk-your-ai-key-here
AI_MODEL=deepseek-chat
```

推荐流程：

```bash
python3 scripts/bootstrap_openclaw.py
```

脚本行为：

- 如果没有安装 OpenClaw CLI，则执行 `npm install -g openclaw@latest`。
- 如果没有 `~/.openclaw/openclaw.json`，则自动部署本机 OpenClaw Gateway。
- 如果已经存在 OpenClaw 配置，则不会重新部署，只同步 Gateway auth 和模型配置。
- 如果本机存在 `wanny/backend/.env` 且项目 `.env` 缺少 `AI_*`，会自动补齐缺失的模型配置。
- 将 Gateway token 同步到 `.env` 和 `backend/.env`。
- 将 `AI_*` 写入本机 OpenClaw 配置，供 launchd Gateway service 使用。
- 设置 OpenClaw 默认模型为 `ceodesk/<AI_MODEL>`。

验证模型：

```bash
openclaw models status --json
openclaw models list --provider ceodesk
```

不要把 `.env`、`backend/.env` 或 `~/.openclaw` 中的密钥复制进文档、issue 或 commit。

## CEO Desk OpenClaw 对接

已实现：

1. Gateway health probe: `GET /api/desk/openclaw/health/`
2. Token handling: 本机 `.env` 和 `backend/.env`，均被 Git 忽略
3. Mission adapter: `POST /api/desk/commands/` 创建 Mission 并调用 `openclaw agent`
4. Streaming logs: `ws://<host>/ws/missions/<mission_id>/logs/`
5. Cost and quality gates: Mission 记录 token usage 和 gateway/model/result/cost gates
