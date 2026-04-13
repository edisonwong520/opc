# OpenClaw Deployment

本项目只支持 OpenClaw，不支持 NanoClaw 或其他 agent runtime。

本文记录 2026-04-13 在当前开发机上的 OpenClaw 本地部署方式，并作为后续 CEO Desk 对接 OpenClaw Gateway 的基线。

## 当前部署结果

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
- RPC probe OK

## Official References

- Installation: https://openclawdoc.com/docs/getting-started/installation/
- CLI Gateway help: https://docs.openclaw.ai/cli/gateway
- CLI Onboard help: https://docs.openclaw.ai/cli/onboard
- Troubleshooting: https://docs.openclaw.ai/troubleshooting

## Install Commands

本机已有 Node.js 24。官方文档要求 Node.js 22+，并推荐 Node.js 24。

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

- `--auth-choice skip` 只部署 Gateway，不在非交互流程里配置模型 provider。
- `--gateway-bind loopback` 只允许本机访问，适合当前开发阶段。
- `--gateway-auth token` 会把 Gateway 保护起来；token 保存在本机 OpenClaw 配置中，不进入项目仓库。
- `--skip-channels` 不配置 Telegram/Discord/WhatsApp 等 channel。CEO Desk 当前只需要 Gateway。

## Verify

```bash
openclaw gateway status
openclaw health
openclaw doctor
```

预期：

- `openclaw gateway status` 显示 `Runtime: running`
- `RPC probe: ok`
- `Listening: 127.0.0.1:7788`

当前 `doctor` 有两个非阻断提醒：

- Gateway 服务使用 nvm 下的 Node。未来 Node 版本升级后，可能需要重新安装 Gateway service。
- bundled Discord voice dependency 未安装。当前未启用 Discord channel，不影响 CEO Desk 的 OpenClaw Gateway 对接。

## Service Commands

```bash
openclaw gateway status
openclaw gateway restart
openclaw gateway stop
openclaw gateway start
openclaw logs
```

## CEO Desk Configuration

后端通过 `OPENCLAW_GATEWAY_URL` 指向 OpenClaw Gateway：

```bash
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:7788
```

当前 CEO Desk 只展示 Gateway 配置和 MVP briefing。下一步接入时，应在后端新增 OpenClaw Gateway client/service，不要在 Django view 里直接拼 RPC 调用。

建议后续对接顺序：

1. Gateway health probe: 后端检查 OpenClaw Gateway 是否在线。
2. Token handling: 将 Gateway token 放入本机 `.env` 或系统 secret，不提交到 Git。
3. Mission adapter: 把 CEO Command 转为 OpenClaw agent/session 请求。
4. Streaming logs: 用 ASGI/WebSocket 把 OpenClaw 执行日志推到前端。
5. Cost and quality gates: 写入任务执行记录、成本统计和质量门结果。

## Reinstall Or Repair

重新部署 service：

```bash
openclaw gateway stop
openclaw gateway install
openclaw gateway start
openclaw gateway status
```

运行自动修复：

```bash
openclaw doctor --fix
```

只有在需要 Discord voice 或迁移 Node runtime 时再运行 `doctor --fix`，当前 MVP 不强制需要。
