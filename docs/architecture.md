# CEO Desk Architecture

## Product Direction

CEO Desk 的核心定位是“CEO 视角的 Agent 公司驾驶舱”，不是传统技术监控面板。用户只需要输入业务目标，系统负责组织角色、拆解任务、并行执行、质检和汇总。

## Tech Choice

本项目采用与 `wanny` 相近的工程形态：

| Layer | Choice | Reason |
| --- | --- | --- |
| Frontend | Vue 3 + Vite + Tailwind | 与 `wanny` 保持一致，启动快，适合快速迭代控制台 |
| Backend | Django 6 + uv | Python 生态友好，便于后续接 OpenClaw/NanoClaw、队列和模型 SDK |
| Local DB | SQLite | MVP 阶段零依赖启动 |
| Runtime | Daphne-ready ASGI | 保留后续 WebSocket/streaming 任务日志空间 |
| Deploy | Docker Compose | 与 `wanny` 的部署习惯一致 |

研究文档中提到 Next.js + React Flow 是可选方向。这里先不引入 React Flow，是为了更快得到一个可运行的 Vue/Django 产品骨架；后续如果组织图交互复杂，可以引入 Vue Flow。

## Backend API

### `GET /api/health/`

返回服务健康状态。

### `GET /api/desk/briefing/`

返回工作台初始数据：

- 产品定位
- OpenClaw Gateway URL
- NanoClaw runtime 配置
- 预设高管团队
- 执行流水线
- MVP 指标

### `POST /api/desk/commands/`

接收 CEO Command，当前返回预览版任务拆解。后续会替换为真实 orchestration：

1. 写入 `Mission`
2. COO 生成任务树
3. 分派到角色 agent
4. 收集执行日志
5. SRE/Quality Gate 检查
6. CEO 汇总报告

## Suggested Domain Model

后续数据库模型建议：

- `AgentTemplate`: 角色名称、职责、tools、模型偏好、预算上限
- `Mission`: 用户指令、状态、优先级、预算、创建者
- `Workstream`: 子任务、owner agent、依赖、状态
- `AgentRun`: runtime session、日志、token、成本、结果
- `QualityGate`: 检查类型、审批状态、阻断原因
- `BoardBrief`: 最终汇总报告、来源引用、决策建议

## OpenClaw/NanoClaw Integration Path

MVP 先通过环境变量保留集成边界：

- `OPENCLAW_GATEWAY_URL`
- `NANOCLAW_BIN`

推荐按三个阶段接入：

1. Gateway health check: 展示 OpenClaw runtime 是否在线。
2. Session adapter: 后端新增 service，负责启动/停止 agent session。
3. Streaming logs: 使用 ASGI/WebSocket 把 agent 输出推到前端 Activity Console。

## Frontend Direction

第一屏就是可操作工作台：

- 左侧是 CEO Command
- 右侧是组织图、指标、执行流水线
- 不做 landing page，避免 MVP 初期被展示层拖慢

视觉方向采用“董事会作战室 + 纸质战略简报”的混合感：高对比黑色控制栏、纸面网格、少量黄/绿/红作为状态色。
