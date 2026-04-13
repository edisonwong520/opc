# CEO Desk

CEO Desk 是一个面向 OpenClaw 的多 Agent 编排管理桌面。它把用户的一句战略指令交给一组预设的 AI 高管角色，由 CEO/COO/CTO/CFO/CMO/SRE 共同拆解、执行、质检和汇报。

当前仓库是 MVP 开发骨架，技术栈参考 `wanny`：

- Backend: Django 6, Daphne, uv, SQLite-first
- Frontend: Vue 3, Vite, Tailwind CSS
- Deploy: Docker Compose, Nginx static frontend, Django API backend

## 协议与使用限制

本项目代码随仓库中的 `LICENSE` 以 GNU Affero General Public License v3.0（AGPL-3.0）发布。

**商业使用限制：未经作者事先书面授权，本项目不得用于商业用途。** 这包括但不限于将本项目或其修改版本用于商业 SaaS、付费托管、企业内部生产系统、商业咨询交付、闭源产品集成、销售或转授权。

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
curl http://127.0.0.1:8000/api/desk/briefing/
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。

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

打开 http://127.0.0.1:8080 。

## OpenClaw

本项目只支持 OpenClaw。当前本机部署记录、验证命令、常见维护命令见 [docs/openclaw-deployment.md](docs/openclaw-deployment.md)。

一键准备 OpenClaw 和模型配置：

```bash
cp .env.example .env
# 填写 AI_BASE_URL、AI_API_KEY、AI_MODEL
python3 scripts/bootstrap_openclaw.py
```

脚本会复用已有 OpenClaw；如果本机还没有 OpenClaw，则自动安装 CLI、部署本机 Gateway，并按 `.env` 配置默认模型。

## MVP 范围

- CEO Command: 输入单一战略指令
- Executive Team: CEO/COO/CTO/CFO/CMO/SRE 角色模板
- Mission Pipeline: Intake、Decomposition、Parallel Work、Quality Gate、Board Brief
- Cost/Risk Placeholder: 预算、质量门、运行时配置占位
- OpenClaw Gateway Placeholder: 后续接入实际 OpenClaw runtime

## 项目结构

```text
backend/
  ceo_desk_server/     Django project
  apps/desk/           CEO Desk API app
frontend/
  src/App.vue          CEO Desk workspace
  src/lib/api.ts       API client
docker/                Container build and nginx config
docs/                  Product and architecture docs
scripts/dev.sh         Local dev runner
```

## 下一步

1. 把 `apps.desk.views` 中的静态角色模板迁移到数据库模型。
2. 增加 Agent Template 编辑能力，生成 OpenClaw 可消费的角色配置。
3. 接入 OpenClaw Gateway，启动真实 agent session。
4. 加入任务状态持久化、执行日志、token 成本统计和质量门审批。
