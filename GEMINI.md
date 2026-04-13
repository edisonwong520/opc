# OPC Project Rules (Common)

作为 AI 助手，在协助开发 OPC 项目时，每次交互都必须遵守以下通用规则。

## 1. 文档定位

- 根目录 `README.md` 用于项目介绍、目录说明、运行方式和 AI 阅读入口。
- 根目录 `GEMINI.md` 仅用于记录通用规则、开发约束与 AI 行为准则。
- 后端专属规则位于 `backend/GEMINI.md`。
- 前端专属规则位于 `frontend/GEMINI.md`。
- 需要了解业务背景、运行方式或部署方式时，优先阅读对应目录下的 `README.md` 或 `docs/` 文档，不要把项目介绍写进规则文件。
- README、用户手册、部署/使用指南等面向用户的文档可以保留中英双语。
- Roadmap、架构计划、开发计划、内部决策记录等过程文档只保留单语，不做中英双语镜像。

## 2. AI 阅读链路

- 第一步：先阅读根目录 `README.md`，了解项目背景与工作区结构。
- 第二步：再阅读根目录 `GEMINI.md`，理解通用规则。
- 第三步：如果任务涉及后端，继续阅读 `backend/GEMINI.md`。
- 第四步：如果任务涉及前端，继续阅读 `frontend/GEMINI.md`。
- 如果是全栈任务，需要同时遵守前后端两个规则文件。
- 如果任务涉及 OpenClaw 部署、Gateway、模型配置或本机环境，优先阅读 `docs/openclaw-deployment.md`。

## 3. 通用开发约束

- OPC 只支持 OpenClaw，不要引入其他 agent runtime 或绕过 `apps.desk.openclaw` 直接调用外部编排系统。
- 密钥、token、模型 API Key、Gateway token 等敏感信息必须只保存在 `.env`、`backend/.env` 或本机 OpenClaw 配置中，严禁写入代码、文档、测试快照或提交信息。
- 后端、前端和 Docker 相关改动应保持在各自工作区内：`backend/`、`frontend/`、`docker/`。
- 所有新增代码应优先沿用现有 Django/Vue/Vite/Tailwind 结构，不为小改动引入新的框架或大型抽象。
- 代码注释统一使用英文；只有在协议边界、异步流程、兼容层、数据映射或维护成本较高时才补充必要注释，避免复述代码字面含义。
- 非用户明确要求时，不主动分析 `git status`、`git diff`、`git log` 或提交历史；只有在用户要求提交、review、追查版本、比较改动时再使用 Git。
- 如果用户要求提交代码，提交信息应使用结构化前缀，如 `feat:`、`fix:`、`refactor:`、`test:`、`docs:`。

## 4. 测试与验证

- 修改后端业务逻辑时，优先补充 Django/pytest 回归测试。
- 修改前端交互或类型结构时，至少运行 `npm run build`，确认 `vue-tsc` 和 Vite build 通过。
- 修改 OpenClaw 集成时，优先验证 `GET /api/opc/openclaw/health/`，并确认 Gateway 和模型状态均可读。
- 验证脚本、一次性调试脚本不得散落在根目录；如果需要长期保留，应放入对应模块的 `tests/` 或 `scripts/` 目录。

## 5. 规则维护

- 新的长期有效规则，应更新到对应的规则文件中：
  - 通用规则更新根目录 `GEMINI.md`
  - 后端规则更新 `backend/GEMINI.md`
  - 前端规则更新 `frontend/GEMINI.md`
- 不要把临时任务计划、个人偏好或一次性排查结论写进规则文件。
