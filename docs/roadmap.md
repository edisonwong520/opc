# OPC Roadmap

Language: English | [Chinese](roadmap.zh-CN.md)

## MVP Status (2026-04-13)

### Completed

- [x] Django backend scaffold with Daphne/ASGI
- [x] Vue 3 + Vite + Tailwind frontend workspace
- [x] Domain models: `AgentTemplate`, `Mission`, `Workstream`, `MissionEvent`, `QualityGate`, `BoardBrief`, `ApprovalDecision`
- [x] OpenClaw Gateway integration (CLI health/model status)
- [x] Single-turn OpenClaw agent execution with WebSocket event streaming
- [x] Mission persistence: command, session, result, token usage, cost estimate
- [x] Quality gates: gateway-health, model-provider, agent-result, cost-capture, founder-approval
- [x] Frontend: command rail, org map, execution pipeline, mission console
- [x] Docker Compose deployment

### Blocked

- [ ] Migration `0002_templates_workstreams_boardbrief.py` pending
- [ ] Migration `0003_approvaldecision.py` pending

---

## Phase 1: Foundation Completion

Priority: Critical | Target: April 2026

### 1.1 Migration Execution

Run pending migrations to activate `ApprovalDecision` and initial data.

```
cd backend
uv run python manage.py migrate
```

### 1.2 Agent Template Editor

**Goal**: Allow the founder to create/edit role templates through the UI.

| Item | Description |
| --- | --- |
| Backend API | `GET/POST /api/opc/templates/` CRUD endpoints |
| Frontend UI | Template editor form: name, title, mission, tools, model preference, budget |
| Output | Generates OpenClaw-compatible agent configuration |

### 1.3 Founder Approval Actions

**Goal**: Allow the founder to approve/reject pending quality gates.

| Item | Description |
| --- | --- |
| Backend API | `POST /api/opc/missions/<id>/approve/` and `/reject/` |
| Frontend UI | Approval buttons on pending `founder-approval` gate |
| Record | `ApprovalDecision` model captures decision, reviewer, notes |

---

## Phase 2: Multi-Agent Delegation

Priority: High | Target: May 2026

### 2.1 Workstream Independence

**Goal**: Each workstream runs its own OpenClaw agent turn.

| Item | Description |
| --- | --- |
| Backend | Replace `_ensure_workstreams` with actual dispatch to COO/CTO/CFO/CMO/SRE |
| Orchestration | Mission starts CEO intake → COO decomposition → parallel work → SRE quality → CEO brief |
| State | Each `Workstream` gets its own `AgentRun` reference |

### 2.2 AgentRun Model

**Goal**: Track individual agent turn execution.

| Field | Description |
| --- | --- |
| `workstream` | ForeignKey to Workstream |
| `session_id` | OpenClaw session for this run |
| `status` | queued/running/succeeded/failed |
| `logs` | JSON array of agent turn events |
| `input_tokens` | Token usage from this run |
| `output_tokens` | Token usage from this run |
| `estimated_cost_usd` | Cost for this turn |
| `result_text` | Final output |

### 2.3 Parallel Execution

**Goal**: CTO/CFO/CMO workstreams run in parallel after COO decomposition.

| Item | Description |
| --- | --- |
| Thread pool | Dispatch parallel agents using `concurrent.futures.ThreadPoolExecutor` |
| Progress | Update each `Workstream.status` independently |
| Consolidation | CEO waits for all parallel workstreams before generating Board Brief |

---

## Phase 3: Cost & Risk Controls

Priority: Medium | Target: June 2026

### 3.1 Model Pricing Profiles

**Goal**: Accurate cost estimation per model/provider.

| Item | Description |
| --- | --- |
| Backend model | `PricingProfile`: provider, model_id, input_per_1k, output_per_1k |
| Admin UI | Django admin for pricing configuration |
| Cost logic | `_estimate_cost` selects profile by `model_preference` |

### 3.2 Budget Enforcement

**Goal**: Stop execution when budget limit is exceeded.

| Item | Description |
| --- | --- |
| Check | Before each agent turn, compare `budget_limit_usd` against cumulative cost |
| Action | If exceeded, fail the workstream with "budget exceeded" |
| Frontend | Show budget warning on mission console |

### 3.3 Rollback & Retry

**Goal**: Recover from failed missions.

| Item | Description |
| --- | --- |
| Retry | `POST /api/opc/missions/<id>/retry/` to re-run failed workstreams |
| Abort | `POST /api/opc/missions/<id>/abort/` to stop running mission |
| Archive | Soft-delete failed missions for audit |

---

## Phase 4: UX Polish

Priority: Low | Target: July 2026

### 4.1 Vue Flow Org Chart

**Goal**: Interactive org chart with drag-and-drop role assignment.

| Item | Description |
| --- | --- |
| Library | Add `@vue-flow/core` and `@vue-flow/renderer` |
| View | Replace static org-map with interactive diagram |
| Action | Click agent node to edit template or view recent runs |

### 4.2 Mission History

**Goal**: Browse past missions with filters.

| Item | Description |
| --- | --- |
| Backend | `GET /api/opc/missions/` with status/date filters |
| Frontend | Mission history list with search |
| Export | Download mission report as PDF/Markdown |

### 4.3 Dashboard Metrics

**Goal**: Real-time metrics on workspace board.

| Item | Description |
| --- | --- |
| Charts | Weekly spend, agent utilization, success rate |
| Update | WebSocket metrics stream every 30s |
| Config | User-defined thresholds for alerts |

---

## Phase 5: Enterprise Readiness

Priority: Future | Target: TBD

### 5.1 Multi-User Authentication

| Item | Description |
| --- | --- |
| Auth | Django auth + JWT or session cookies |
| Teams | Each user belongs to an organization |
| Scope | Missions/templates scoped to organization |

### 5.2 Postgres Migration

| Item | Description |
| --- | --- |
| DB | Replace SQLite with PostgreSQL |
| Migration | Django migrate to Postgres |
| Backup | Automated backup schedule |

### 5.3 Audit Log

| Item | Description |
| --- | --- |
| Model | `AuditLog`: user, action, entity, timestamp, metadata |
| Scope | All template edits, mission creates, approvals logged |

---

## Immediate Action Items

1. Run `uv run python manage.py migrate` in backend
2. Implement Agent Template CRUD API (`backend/apps/desk/views.py`)
3. Add template editor Vue component (`frontend/src/components/TemplateEditor.vue`)
4. Implement approval API endpoints
5. Add approval buttons to mission console

---

## Notes

- Roadmap reflects README.md "Next Steps" plus architecture growth
- Phase sequence prioritizes MVP completion before multi-agent orchestration
- Commercial license restrictions apply per LICENSE file