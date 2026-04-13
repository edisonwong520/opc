# OPC Backend Rules

本文件只记录后端开发规则。处理后端任务时，除根目录 `README.md` 与根目录 `GEMINI.md` 外，还必须阅读本文件。

## 1. 技术栈与基础约束

- 核心框架：Python 3.12+、Django 6、Daphne/ASGI、Channels。
- 包管理工具：必须优先使用 `uv`，例如 `uv sync`、`uv add`、`uv run`。
- 本地数据库默认使用 SQLite；除非任务明确要求，不要切换到 PostgreSQL 或其他数据库。
- 配置读取优先通过 Django settings 与 `.env`，禁止硬编码 API Key、Gateway token、数据库密码等敏感信息。
- 后端业务时间应使用 Django timezone API，避免直接使用 naive datetime。

## 2. OpenClaw 集成边界

- OpenClaw 访问必须封装在 `apps.desk.openclaw` 内。Views、models、consumers 不应直接拼接 `openclaw` CLI 命令或读取 `~/.openclaw`。
- Gateway URL、auth mode、token、password 必须从 settings/env 读取。
- 任务执行、Gateway health、model status、usage/cost 等能力应通过服务函数暴露给 view 层。
- 任何对 OpenClaw CLI 输出的解析都必须容忍非 JSON 日志前缀，不能假设 stdout 是纯 JSON。
- 当前 MVP 是 single-turn OpenClaw mission；实现多 workstream 独立执行时，应保留 mission/event/gate 的审计记录。

## 3. API 与模型规范

- API 返回字段使用前端已采用的 camelCase；Django model 字段保持 snake_case。
- Mission、Workstream、QualityGate、BoardBrief、ApprovalDecision 等序列化逻辑优先集中在 `apps.desk.openclaw`，避免在多个 view 中重复拼响应结构。
- 新增状态值必须同步更新模型 choices、序列化、前端 TypeScript 类型和测试。
- 新增数据库字段必须创建 migration，并运行 `uv run python manage.py migrate` 验证。
- 质量门和审批记录是审计数据，不要在普通状态更新中删除历史 `ApprovalDecision`。

## 4. 测试规范

- 常规后端验证命令：`uv run pytest`。
- Python 测试文件优先使用 `test_*.py` 命名；已有 Django app 的 `tests.py` 可继续保留，但新增复杂测试应拆入 app 内 `tests/` 目录。
- 测试应包含明确业务断言，不只验证接口不报错。
- 对模板 CRUD、mission 创建、审批、OpenClaw health/model status 等接口改动，必须补充或更新回归测试。
- 测试不得依赖真实 API Key 或真实付费模型调用；需要 OpenClaw 行为时应 mock 服务函数或只验证本地 health 解析逻辑。

## 5. 运行与排障

- 本地后端启动命令：

```bash
cd backend
uv run python manage.py runserver 0.0.0.0:8000
```

- 修改环境配置后，优先检查：

```bash
cd backend
uv run python manage.py migrate
curl http://127.0.0.1:8000/api/opc/openclaw/health/
```
