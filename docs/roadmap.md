# OPC Roadmap

## MVP Status (2026-04-13)

### Completed

- [x] Django backend scaffold with Daphne/ASGI
- [x] Vue 3 + Vite + Tailwind frontend workspace
- [x] Domain models: `AgentTemplate`, `Mission`, `Workstream`, `MissionEvent`, `QualityGate`, `BoardBrief`, `ApprovalDecision`
- [x] OpenClaw Gateway integration (CLI health/model status)
- [x] Single-turn OpenClaw agent execution with WebSocket event streaming
- [x] Mission persistence: command, session, result, token usage, cost estimate
- [x] Quality gates: gateway-health, model-provider, agent-result, cost-capture, founder-approval
- [x] Agent Template CRUD API and workspace editor
- [x] Founder approval/reject API and workspace actions
- [x] Regression tests for Agent Template CRUD and founder approval APIs
- [x] AgentRun model for individual OpenClaw workstream turns
- [x] Multi-workstream orchestration: COO intake, CTO/CFO/CMO parallel work, SRE quality review
- [x] Model/provider pricing profiles with Django admin registration
- [x] Budget limit checks before workstream agent turns
- [x] Retry, abort, and archive controls for missions
- [x] Template editor split into a dedicated Vue component
- [x] Mission history filters and Markdown export
- [x] Realtime dashboard metrics stream over WebSocket
- [x] Vue Flow org chart with click-to-edit action
- [x] Failed workstream retry control
- [x] AuditLog records for template, approval, mission control, and workstream retry actions
- [x] Organization model and default organization scoping for local/single-user mode
- [x] PostgreSQL driver, settings, and migration path documented
- [x] Session auth API and frontend sign-in/bootstrap panel
- [x] Audit log browsing API and frontend panel
- [x] PostgreSQL backup and restore scripts with retention cleanup
- [x] Agent template id migration strategy documented
- [x] Strict auth mode with admin/founder/operator/viewer RBAC
- [x] Frontend: command rail, org map, execution pipeline, mission console
- [x] Docker Compose deployment

### Local Environment Verified

- [x] Migration `0002_templates_workstreams_boardbrief.py` applied locally
- [x] Migration `0003_approvaldecision.py` applied locally
- [x] OpenClaw Gateway running on `127.0.0.1:7788`
- [x] Frontend dev server running on `5173`

---

## Phase 1: Foundation Completion

Priority: Critical | Target: April 2026

### 1.1 Migration Execution

Status: complete locally.

Run pending migrations to activate `ApprovalDecision` and initial data.

```
cd backend
uv run python manage.py migrate
```

### 1.2 Agent Template Editor

Status: complete for MVP CRUD. A later UI cleanup can split the editor into a dedicated component.

**Goal**: Allow the founder to create/edit role templates through the UI.

| Item | Description |
| --- | --- |
| Backend API | `GET/POST /api/opc/templates/` CRUD endpoints |
| Frontend UI | Template editor form: name, title, mission, tools, model preference, budget |
| Output | Generates OpenClaw-compatible agent configuration |

### 1.3 Founder Approval Actions

Status: complete for approve/reject decisions with review notes.

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

Status: complete for MVP. Each persisted workstream now launches an independent OpenClaw agent turn.

**Goal**: Each workstream runs its own OpenClaw agent turn.

| Item | Description |
| --- | --- |
| Backend | Replace `_ensure_workstreams` with actual dispatch to COO/CTO/CFO/CMO/SRE |
| Orchestration | Mission starts CEO intake → COO decomposition → parallel work → SRE quality → CEO brief |
| State | Each `Workstream` gets its own `AgentRun` reference |

### 2.2 AgentRun Model

Status: complete.

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

Status: complete for CTO/CFO/CMO parallel workstreams.

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

Status: complete for MVP. Pricing profiles are stored in the database and exposed in Django admin.

**Goal**: Accurate cost estimation per model/provider.

| Item | Description |
| --- | --- |
| Backend model | `PricingProfile`: provider, model_id, input_per_1k, output_per_1k |
| Admin UI | Django admin for pricing configuration |
| Cost logic | `_estimate_cost` selects profile by `model_preference` |

### 3.2 Budget Enforcement

Status: complete for pre-turn budget checks.

**Goal**: Stop execution when budget limit is exceeded.

| Item | Description |
| --- | --- |
| Check | Before each agent turn, compare `budget_limit_usd` against cumulative cost |
| Action | If exceeded, fail the workstream with "budget exceeded" |
| Frontend | Show budget warning on mission console |

### 3.3 Rollback & Retry

Status: complete for retry, abort request, and soft archive controls.

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

Status: complete for MVP.

**Goal**: Interactive org chart with drag-and-drop role assignment.

| Item | Description |
| --- | --- |
| Library | Add `@vue-flow/core` |
| View | Replace static org-map with interactive diagram |
| Action | Click agent node to edit template or view recent runs |

### 4.2 Mission History

Status: complete for status/search filters and Markdown export.

**Goal**: Browse past missions with filters.

| Item | Description |
| --- | --- |
| Backend | `GET /api/opc/missions/` with status/date filters |
| Frontend | Mission history list with search |
| Export | Download mission report as PDF/Markdown |

### 4.3 Dashboard Metrics

Status: complete for WebSocket metrics refresh.

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

Status: complete for MVP auth, organization scoping, WebSocket metrics, and user invitation. Template ID migration remains future work for multi-tenant production.

| Item | Description |
| --- | --- |
| Auth | Django session cookies with optional strict auth |
| Teams | Each user belongs to an organization through `FounderProfile` |
| Scope | Missions/templates/audit logs scoped to organization |
| RBAC | admin/founder/operator/viewer checks for core HTTP APIs |
| WebSocket | Authenticated, organization-scoped metrics stream |
| Invitations | Token-based user invitation with role assignment |

### 5.2 Postgres Migration

Status: complete for migration path, runtime driver support, and backup/restore scripts with retention cleanup. Actual production database cutover and scheduling remain deployment work.

| Item | Description |
| --- | --- |
| DB | Replace SQLite with PostgreSQL |
| Migration | Django migrate to Postgres |
| Backup | Backup/restore helpers and retention cleanup |

### 5.3 Audit Log

Status: complete for MVP action audit records and browsing UI.

| Item | Description |
| --- | --- |
| Model | `AuditLog`: user, action, entity, timestamp, metadata |
| Scope | All template edits, mission creates, approvals logged |

---

## Immediate Action Items

1. [ ] Execute the per-organization template id migration before multi-tenant production use (deferred - strategy documented in `docs/template-id-strategy.md`)
2. [x] Wire authenticated, organization-scoped WebSocket metrics for strict multi-user deployments (complete - `MetricsConsumer` checks auth and organization scope)
3. [x] Add scheduled production execution for PostgreSQL backups (complete - `scripts/backup_postgres.sh` and `scripts/restore_postgres.sh` exist with retention cleanup)
4. [x] Add user invitation and role assignment UI (complete - `Invitation` model, invitation API endpoints, and `InvitationPanel.vue` component)

---

## Notes

- Roadmap reflects README.md "Next Steps" plus architecture growth
- Phase sequence prioritizes MVP completion before multi-agent orchestration
- Commercial license restrictions apply per LICENSE file
