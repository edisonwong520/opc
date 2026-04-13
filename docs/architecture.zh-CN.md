# CEO Desk 架构

语言：[English](architecture.md) | 中文

## 产品方向

CEO Desk 是一个面向 CEO 视角的 OpenClaw AI 公司驾驶舱，不是通用技术监控面板。用户输入业务目标，系统负责组织角色、拆解任务、执行 agent turn、检查质量，并返回高管汇报。

## 技术选择

本项目采用与 `wanny` 相近的工程形态：

| Layer | Choice | Reason |
| --- | --- | --- |
| Frontend | Vue 3 + Vite + Tailwind | 与 `wanny` 保持一致，启动快，适合快速迭代控制台 |
| Backend | Django 6 + uv | Python 生态友好，便于接 OpenClaw、队列、模型 SDK 和后续编排 |
| Local DB | SQLite | MVP 阶段零依赖启动 |
| Runtime | Daphne-ready ASGI | 为 WebSocket mission logs 和流式活动保留空间 |
| Deploy | Docker Compose | 与 `wanny` 的部署习惯一致 |

研究文档中提到 Next.js + React Flow 是可选方向。这里先采用 Vue/Django，以保持与 `wanny` 一致；后续组织图交互复杂时，可以引入 Vue Flow。

## 后端 API

### `GET /api/health/`

返回基础服务健康状态。

### `GET /api/desk/briefing/`

返回工作台初始数据：

- 产品定位
- OpenClaw Gateway URL
- OpenClaw Gateway 健康状态
- 默认 OpenClaw 模型状态
- 高管团队模板
- 执行流水线
- MVP 指标

### `POST /api/desk/commands/`

创建 `Mission`，启动后台 OpenClaw agent turn，并返回 mission 记录。

当前流程：

1. 写入 `Mission`
2. 初始化质量门
3. 检查 Gateway health
4. 检查默认模型 provider
5. 执行 `openclaw agent --session-id <id> --message <command> --json`
6. 存储最终回复、raw result、token usage 和质量门结果
7. 通过 WebSocket 推送 mission events

### `GET /api/desk/missions/<mission_id>/`

返回 mission 状态、events、quality gates、结果文本和 token usage。

### `GET /api/desk/openclaw/health/`

返回 Gateway health 和模型 provider health。

### `GET /api/desk/openclaw/logs/`

通过 CLI log reader 返回最近的 OpenClaw Gateway logs。

### `GET /api/desk/openclaw/cost/`

当本机 Gateway pairing scope 允许时，返回 Gateway usage-cost 数据。Mission 级 token usage 仍会直接从 `openclaw agent --json` 捕获。

## WebSocket

Mission events 通过以下地址推送：

```text
ws://127.0.0.1:8000/ws/missions/<mission_id>/logs/
```

每条消息是一个 `MissionEvent` JSON 对象。

## 领域模型

- `Mission`: 用户指令、OpenClaw session id、状态、结果、raw output 和 token usage
- `MissionEvent`: append-only mission log 和状态流
- `QualityGate`: gateway health、model provider、agent result、cost capture 检查

后续模型：

- `AgentTemplate`: 角色名称、职责、tools、模型偏好、预算上限
- `Workstream`: 子任务、owner agent、依赖、状态
- `AgentRun`: runtime session、日志、token usage、成本、结果
- `BoardBrief`: 带来源引用和建议的最终高管报告

## OpenClaw 边界

后端把 OpenClaw 访问封装在 `apps.desk.openclaw`。Views 不应直接拼 CLI 或 Gateway 调用。

环境变量边界：

- `OPENCLAW_GATEWAY_URL`
- `OPENCLAW_GATEWAY_AUTH_MODE`
- `OPENCLAW_GATEWAY_TOKEN`
- `OPENCLAW_GATEWAY_PASSWORD`
- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

## 前端方向

第一屏就是可操作工作台：

- 左侧：CEO Command
- 主工作区：Gateway/model status、org map、metrics、mission pipeline
- Mission console：live events、quality gates、结果文本和 token usage

MVP 不做 landing page，直接进入操作体验。

视觉方向是“董事会作战室”：高对比 command rail、纸面网格、克制的黄/绿/红状态色。
