# OPC Frontend Rules

本文件只记录前端开发规则。处理前端任务时，除根目录 `README.md` 与根目录 `GEMINI.md` 外，还必须阅读本文件。

## 1. 技术栈

- 框架与构建：Vue 3、Vite、TypeScript。
- Node 推荐版本：`24.11.1` 或 Node 22+。
- 样式系统：Tailwind CSS 与 `src/style.css` 中的项目样式。
- API client 统一放在 `src/lib/api.ts`，组件不直接散落 fetch URL 拼接逻辑。

## 2. 前端开发约束

- 主体验是 OPC workspace，不要默认做营销 landing page。
- 所有页面和组件必须支持响应式布局，兼容桌面与移动端。
- UI 应保持克制、清晰、稳定，避免廉价感、过度装饰和无意义动效。
- 按钮、输入框、弹窗、卡片圆角不超过 8px，除非现有局部样式已有明确例外。
- 不使用大面积单色系主题，不引入紫色/蓝紫渐变、米色/沙色、深蓝/ slate 或棕橙咖啡色作为主视觉。
- 文案只写用户可见的产品语言，不写“此处显示”“该界面包含”等自描述说明。
- 组件状态变化不能造成明显布局跳动；固定格式 UI 应使用稳定尺寸、grid 或响应式约束。

## 3. 数据与状态

- 前端类型必须与后端 API 序列化字段同步更新。
- Mission、QualityGate、ApprovalDecision、AgentTemplate 等共享类型优先维护在 `src/lib/api.ts`。
- WebSocket mission logs 只负责增量事件；最终 mission 状态仍应通过 `fetchMission` 拉取后端权威数据。
- 用户触发的 approve/reject、template save/delete 等操作必须处理 loading 状态和错误状态。

## 4. 验证

- 修改前端代码后，至少运行：

```bash
cd frontend
npm run build
```

- 修改 API contract 时，还要确认后端测试通过：

```bash
cd backend
uv run pytest
```

- 本地前端启动命令：

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```
