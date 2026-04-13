# OPC

语言：[English](README.md) | 中文

OPC（One Person Company）是一个只面向 OpenClaw 的多 Agent 编排管理桌面。它把用户的一句创始人指令交给一组预设的 AI 高管角色，由 CEO、COO、CTO、CFO、CMO、SRE 协同拆解、执行、质检和汇报。

当前仓库是 MVP 开发骨架，技术栈参考本机 `wanny` 项目：

- Backend: Django 6, Daphne, uv, SQLite-first
- Frontend: Vue 3, Vite, Tailwind CSS
- Deploy: Docker Compose, Nginx static frontend, Django API backend

## 协议与使用限制

本项目代码随仓库中的 `LICENSE` 以 GNU Affero General Public License v3.0（AGPL-3.0）发布。

**未经作者事先书面授权，本项目不得用于商业用途。** 这包括但不限于商业 SaaS、付费托管、企业内部生产系统、商业咨询交付、闭源产品集成、销售或转授权。

如需商业使用、闭源集成、私有部署授权或其他 AGPL-3.0 之外的授权，请先联系作者获得单独的商业许可。

## 快速启动

### 1. 后端

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

检查 API：

```bash
curl http://127.0.0.1:8000/api/health/
curl http://127.0.0.1:8000/api/opc/briefing/
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173。

### 3. 一键开发启动

```bash
./scripts/dev.sh
```

这个脚本会分别启动后端 `8000` 和前端 `5173`。

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

打开 http://127.0.0.1:8080。

## OpenClaw

本项目只支持 OpenClaw。部署记录、验证命令和维护命令见 [docs/openclaw-deployment.zh-CN.md](docs/openclaw-deployment.zh-CN.md)。

一键准备 OpenClaw 和模型配置：

```bash
cp .env.example .env
# 填写 AI_BASE_URL、AI_API_KEY、AI_MODEL
python3 scripts/bootstrap_openclaw.py
```

脚本会复用已有 OpenClaw；如果本机还没有 OpenClaw，则自动安装 CLI、部署本机 Gateway，并按 `.env` 配置默认模型。

## MVP 范围

- Founder Command: 输入单一战略指令
- Executive Team: 数据库持久化的 CEO/COO/CTO/CFO/CMO/SRE 角色模板
- Mission Pipeline: Intake、Decomposition、Parallel Work、Quality Gate、Board Brief
- Workstreams: 每个 mission 持久化 COO/CTO/CFO/CMO/SRE workstream 记录
- Board Brief: 持久化高管摘要、建议、风险和来源
- Cost/Risk: token usage、可配置成本估算费率、质量门和 founder approval 状态
- OpenClaw Gateway: 本机 Gateway 配置与健康状态
- OpenClaw Mission Adapter: 后端创建 Mission、调用 OpenClaw agent、通过 WebSocket 推送日志并记录 token usage

## 项目结构

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

## 下一步

1. 增加 Agent Template 编辑能力，生成 OpenClaw 可消费的角色配置。
2. 将 Mission adapter 从“单次 OpenClaw 调用 + workstream 表示”扩展为真正独立委派的多 workstream。
3. 在 UI 中增加 founder approval 操作，让 pending approval gates 可以被批准或拒绝。
4. 为不同 model/provider 增加更细的成本定价配置。
