# 开发指南

语言：[English](development.md) | 中文

## 环境要求

- Python 3.12+
- uv
- Node.js 22+
- npm
- Docker Desktop，可选

## 后端命令

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

运行测试：

```bash
cd backend
uv run pytest
```

## 前端命令

```bash
cd frontend
npm install
npm run dev
npm run build
```

## 环境变量

后端环境变量位于 `backend/.env`。

重要变量：

- `DJANGO_DEBUG`: 本地开发时为 `true`
- `DJANGO_ALLOWED_HOSTS`: 逗号分隔的 host allowlist
- `DJANGO_CORS_ALLOWED_ORIGINS`: 前端开发源
- `OPENCLAW_GATEWAY_URL`: OpenClaw Gateway endpoint
- `OPENCLAW_GATEWAY_AUTH_MODE`: Gateway auth mode，通常是 `token`
- `OPENCLAW_GATEWAY_TOKEN`: 本机 Gateway token，不能提交
- `AI_BASE_URL`: OpenAI-compatible 模型 endpoint
- `AI_API_KEY`: 模型 API key，不能提交
- `AI_MODEL`: OpenClaw bootstrap 使用的默认模型 id
- `OPC_COST_INPUT_PER_1K_USD`: 可选的 input token 估算费率
- `OPC_COST_OUTPUT_PER_1K_USD`: 可选的 output token 估算费率

前端环境变量：

- `VITE_API_BASE_URL`: 生产构建时可选的 API base URL

本地 Vite 开发时，`/api` 会代理到 `http://127.0.0.1:8000`。

## 编码说明

- Agent orchestration 必须封装在后端 service module 中，不要从 view 直接调用 runtime。
- 模板应通过 `AgentTemplate` 保持 data-driven，不要在 views 中重新写死角色数据。
- Mission 持久化应围绕 `Mission`、`Workstream`、`MissionEvent`、`QualityGate`、`BoardBrief`。
- Cost tracking 和 quality gates 是一等产品能力，不是后补项。
