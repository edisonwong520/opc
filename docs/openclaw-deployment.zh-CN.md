# OpenClaw 部署

语言：[English](openclaw-deployment.md) | 中文

OPC 只支持 OpenClaw，不支持其他 agent runtime。

本文记录 OPC 的本机 OpenClaw 部署基线。

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
- `--skip-channels` 跳过 Telegram、Discord、WhatsApp 等 channel。OPC 当前只需要 Gateway。

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
- bundled Discord voice dependency 未安装。当前未启用 Discord channel，不影响 OPC。

## 服务命令

```bash
openclaw gateway status
openclaw gateway restart
openclaw gateway stop
openclaw gateway start
openclaw logs
```

## OPC 配置

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
- 设置 OpenClaw 默认模型为 `opc/<AI_MODEL>`。

验证模型：

```bash
openclaw models status --json
openclaw models list --provider opc
```

不要把 `.env`、`backend/.env` 或 `~/.openclaw` 中的密钥复制进文档、issue 或 commit。

## Gateway Pairing

使用 Gateway 模式时，OpenClaw 需要 device pairing 才能执行管理 RPC。如果 pairing 处于 pending 状态，agent 连接会失败并显示 `gateway connect failed: pairing required`，然后 fallback 到 embedded 模式。

### 症状

- `openclaw gateway status` 显示 `pairing required`
- Agent 执行失败并显示 `gateway connect failed: pairing required`
- `openclaw gateway usage-cost` 返回权限错误

### 解决方案

批准 pending pairing 请求：

```bash
# 列出 pending 请求
openclaw devices list --json

# 批准特定请求
openclaw devices approve <request-id>

# 或批准最新的 pending 请求
openclaw devices approve --latest
```

### 自动批准

bootstrap 脚本包含自动 pairing 批准：

```bash
python3 scripts/bootstrap_openclaw.py
```

脚本会：
1. 检查 pending pairing 请求
2. 自动批准它们
3. 验证 Gateway 连接

如果希望手动批准，请在执行 agent 前检查 `openclaw devices list`。

## OPC Agent Profile

OpenClaw agents 需要访问项目文件。workspace 通过 OPC agent profile 配置，而非 subprocess cwd。

### 预设配置文件

OPC 在 `openclaw/` 目录包含预设的 agent 配置文件：

| 文件 | 用途 |
| --- | --- |
| `AGENTS.md` | Agent 身份、能力、输出格式 |
| `SOUL.md` | Agent 人格、沟通风格 |
| `USER.md` | 创始人画像、决策标准 |

bootstrap 脚本会在配置时将这些文件复制到 `~/.openclaw/agents/opc/agent/`。

### 配置

bootstrap 脚本配置 OPC agent profile：

- Agent ID: `opc`
- Workspace: `<project-root>` (例如 `/Users/edison/code/python/opc`)
- Agent directory: `~/.openclaw/agents/opc/agent`

这让 agents 可以读取项目文件如 `README.md`、`docs/`、`backend/` 等。

### 验证

```bash
openclaw config get agents.list
ls ~/.openclaw/agents/opc/agent/
```

预期输出包含：

```json
[
  {
    "id": "opc",
    "workspace": "/Users/edison/code/python/opc",
    "agentDir": "~/.openclaw/agents/opc/agent"
  }
]
```

以及 agent 目录文件：

```
AGENTS.md  SOUL.md  USER.md
```

### 使用方式

后端调用使用 `--agent opc` 确保 workspace 正确：

```python
command = [
    "openclaw",
    "agent",
    "--agent",
    "opc",
    "--session-id",
    session_id,
    "--message",
    prompt,
]
```

## OPC OpenClaw 对接

已实现：

1. Gateway health probe: `GET /api/opc/openclaw/health/`
2. Token handling: 本机 `.env` 和 `backend/.env`，均被 Git 忽略
3. Mission adapter: `POST /api/opc/commands/` 创建 Mission 并调用 `openclaw agent`
4. Streaming logs: `ws://<host>/ws/missions/<mission_id>/logs/`
5. Cost and quality gates: Mission 记录 token usage 和 gateway/model/result/cost gates
