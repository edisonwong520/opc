# OPC Backend

语言：English | [中文](README.zh-CN.md)

OPC (One Person Company) 多智能体编排台的 Django API 后端。基于 Django 6、Daphne/ASGI 和 Channels 构建，支持 WebSocket 实时通信。

## 环境配置

后端从**项目根目录 `.env`** 文件（上级目录）读取环境变量。不要在 `backend/` 目录内创建 `.env`。

```bash
# 在项目根目录执行
cp .env.example .env
# 编辑 .env 配置你的参数
```

主要环境变量：

| 变量 | 说明 |
|------|------|
| `DJANGO_SECRET_KEY` | Django 密钥 |
| `DJANGO_DEBUG` | 调试模式 (true/false) |
| `DJANGO_ALLOWED_HOSTS` | 允许的主机，逗号分隔 |
| `DJANGO_CORS_ALLOWED_ORIGINS` | CORS 允许来源，逗号分隔 |
| `DB_ENGINE` | 数据库引擎 (sqlite3 或 postgresql) |
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway WebSocket 地址 |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw Gateway 认证令牌 |
| `AI_BASE_URL` | OpenAI 兼容 API 基地址 |
| `AI_API_KEY` | AI API 密钥 |
| `AI_MODEL` | 模型标识符 |
| `OPC_REQUIRE_AUTH` | 是否需要认证 (true/false) |

## 本地开发

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

通过 Daphne 启动 WebSocket 支持：

```bash
uv run daphne -b 0.0.0.0 -p 8000 opc_server.asgi:application
```

## 测试

```bash
uv run pytest
```

## API 接口

所有接口位于 `/api/opc/` 下：

### 认证

| 方法 | 接口 | 说明 |
|------|------|------|
| GET | `/api/opc/auth/me/` | 当前用户信息 |
| POST | `/api/opc/auth/login/` | 登录 |
| POST | `/api/opc/auth/logout/` | 登出 |
| POST | `/api/opc/auth/bootstrap/` | 初始化创始人账户 |

### 任务

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/opc/commands/` | 从命令创建任务 |
| GET | `/api/opc/missions/` | 任务列表（支持过滤） |
| GET | `/api/opc/missions/<id>/` | 任务详情 |
| POST | `/api/opc/missions/<id>/approve/` | 批准任务 |
| POST | `/api/opc/missions/<id>/reject/` | 拒绝任务 |
| POST | `/api/opc/missions/<id>/retry/` | 重试失败工作流 |
| POST | `/api/opc/missions/<id>/abort/` | 终止运行中的任务 |
| POST | `/api/opc/missions/<id>/archive/` | 归档任务 |
| GET | `/api/opc/missions/<id>/export/` | 导出任务为 Markdown |
| POST | `/api/opc/missions/<id>/workstreams/<ws_id>/retry/` | 重试指定工作流 |

### 智能体模板

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/opc/templates/` | 创建模板 |
| PATCH | `/api/opc/templates/<id>/` | 更新模板 |

### OpenClaw 集成

| 方法 | 接口 | 说明 |
|------|------|------|
| GET | `/api/opc/openclaw/health/` | Gateway 健康状态 |
| GET | `/api/opc/openclaw/logs/` | Gateway 最近日志 |
| GET | `/api/opc/openclaw/cost/` | Token 使用量和成本 |

### 审计与邀请

| 方法 | 接口 | 说明 |
|------|------|------|
| GET | `/api/opc/audit-logs/` | 浏览审计记录 |
| GET | `/api/opc/invitations/` | 邀请列表 |
| POST | `/api/opc/invitations/create/` | 创建邀请 |
| POST | `/api/opc/invitations/<token>/accept/` | 接受邀请 |
| POST | `/api/opc/invitations/<id>/revoke/` | 撤销邀请 |

### 其他

| 方法 | 接口 | 说明 |
|------|------|------|
| GET | `/api/opc/briefing/` | 仪表板简报 |
| GET | `/api/health/` | API 健康检查 |

## WebSocket

指标流位于 `/ws/metrics/`：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics/');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## PostgreSQL 迁移

生产环境建议从 SQLite 切换到 PostgreSQL：

1. 更新 `.env`：
   ```bash
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=opc
   DB_USER=opc
   DB_PASSWORD=your-password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   ```

2. 执行迁移：
   ```bash
   uv run python manage.py migrate
   ```

3. 使用备份脚本：
   ```bash
   scripts/backup_postgres.sh
   scripts/restore_postgres.sh
   ```

## 项目结构

```
backend/
├── opc_server/        # Django 项目配置
│   ├── settings.py    # 环境加载的设置
│   ├── urls.py        # 根 URL 路由
│   ├── asgi.py        # ASGI 应用
│   └── wsgi.py        # WSGI 应用
├── apps/
│   └── desk/          # OPC API 应用
│       ├── models.py  # Mission、Workstream、Template 等模型
│       ├── views.py   # API 接口
│       ├── urls.py    # 应用 URL 路由
│       ├── openclaw/  # OpenClaw 集成服务
│       └── tests/     # pytest 测试
├── pyproject.toml     # uv 包配置
└── README.md
```

## 依赖

- Django 6.0+
- Daphne 4.2+ (ASGI 服务器)
- Channels 4.3+ (WebSocket)
- django-cors-headers
- psycopg (PostgreSQL 驱动)
- python-dotenv