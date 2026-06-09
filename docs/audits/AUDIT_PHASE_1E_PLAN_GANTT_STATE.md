# AUDIT Phase 1E · M17 Plan Gantt cliente Empirical State

**Sesión**: 3B-2B.8 CLUSTER 1 Phase 1E
**Fecha**: 2026-05-26
**Status**: ✅ **ADDRESSED · Phase 1E shipped commit `4d3fb18`** (CLUSTER 1 cierre validation 2026-05-26)

> **Closure**: GanttView named export refactor implemented · backward-compat preserved (default PlanGantt unchanged). 5/5 backend tests PASS · 68/68 m17_planning regression. ADR-014 sostained empirical (405 PATCH/PUT/DELETE asserted cliente endpoint). 4 Future-X captured (tooltip ENS · mobile vertical · export PDF/iCal · progress celebration).

---

## Resumen ejecutivo

Briefing Phase 1E asumió `m04_plan` motor + `frontend/components/m17_planning/*` + `assigned_to_role` field. Empirical reality (mixed):

- ❌ **Motor name**: `m04_plan` NOT exists · canonical es `m17_planning`
- ✅ **Gantt component EXISTS**: [frontend/components/project/PlanGantt.tsx](../../frontend/components/project/PlanGantt.tsx) (NOT `m17_planning/*` location)
- ✅ **PlanGantt YA es READ-ONLY** (no edit/drag interactions · perfect cliente reuse)
- ❌ **Field `assigned_to_role` NOT exists** · empirical es `WbsTask.responsible: str` con valores `'marcos'|'cliente'|'plataforma'|'mixto'`
- ✅ **Auditor portal PlanView existe** (READ-ONLY pattern reference) · proves Gantt reuse cross-portal feasible
- ✅ **Admin endpoint timeline**: `GET /api/v1/projects/{project_id}/timeline` returns full `TimelineResponse` (tasks + milestones + plan_start/end)

**OPS-052 trigger evaluation**: mismatch ~40-50% briefing/empirical pero TODOS los componentes existen · solo cambian nombres + locations · arquitectura cliente-reuse clara · **NO STOP HARD necesario** · proceed normal con scope ajustado.

ETA refined ~2.5-3.5h vs briefing ~3-5h (-25% OPS-045 sostained gracias Gantt reuse + endpoint timeline existing).

---

## Phase 1E.0.1 · PlanGantt component empirical

**Path**: [frontend/components/project/PlanGantt.tsx](../../frontend/components/project/PlanGantt.tsx) (348 LOC)

Características:
- 100% READ-ONLY · NO drag/drop · NO inline edit · NO context menus
- Internal `useQuery` con `api()` admin client · fetcher hard-coupled
- Internal `GanttView` extracted como sub-component (private)
- Renders SVG bars + milestone diamonds + critical path stroke red + month markers
- Spanish locale (`toLocaleDateString("es-ES")`)
- Auth coupling: ÚNICA dependencia admin específica es `api()` import (línea 28)

**Decisión reuse**: refactor PlanGantt para export `GanttView` como named export + opcional `fetchFn` prop override. Cliente page pasa custom fetcher via `clientApi`. OPS-026 DRY sostained.

## Phase 1E.0.2 · Backend M17 endpoints empirical

**Motor real**: `m17_planning` (NOT `m04_plan`)

Endpoints relevantes:
- `GET /api/v1/projects/{project_id}/timeline` (admin auth · returns full TimelineResponse)
- `POST /api/v1/planning/projects/{project_id}/generate` (admin · genera plan)
- `PATCH /api/v1/planning/tasks/{task_id}` (admin · update status/progress/blocker)

Schemas backend:
- `TimelineResponse{plan_start, plan_end, tasks: list[TimelineTask], milestones, plan_estado}` ([backend/app/api/v1/projects.py:319](../../backend/app/api/v1/projects.py#L319))
- `TimelineTask{id, task_code, task_name, phase, start_date, end_date, status, progress_pct, is_critical_path}`
- NO field `responsible` en TimelineTask schema (presente en ORM `WbsTask` pero filtered out)

**Acción Phase 1E**: NEW cliente endpoint `GET /api/v1/client-portal/plan` reusando `get_project_timeline` logic + add `responsible` field exposición + audit_log emit + R29 friendly.

## Phase 1E.0.3 · Cliente assignment fields empirical

**WbsTask schema** ([backend/app/models/planning.py:44](../../backend/app/models/planning.py#L44)):
- `responsible: str | None` (NOT enum)
- Values empirical from `WBSTaskTemplate.responsible` comment + catalog: `'marcos' | 'cliente' | 'plataforma' | 'mixto'`

**Cliente filter "Solo mis tareas"**: `responsible IN ('cliente', 'mixto')` · mixto incluye cliente parcial.

## Phase 1E.0.4 · Reuse decision documented

| Decision | Approach | Rationale |
|----------|----------|-----------|
| Gantt reuse | Refactor PlanGantt export `GanttView` + optional `fetchFn` prop | DRY OPS-026 · backward-compat preserved (default fetcher) · cliente custom fetcher |
| Backend motor | Use empirical `m17_planning` naming | Briefing mismatch corrected · SSE event uses `m17.plan.updated` |
| Cliente endpoint | NEW `GET /api/v1/client-portal/plan` mirrors TimelineResponse shape + `responsible` field exposed | ADR-013 doble pool · audit_log emit Sub-atom 5.A |
| Filter "mis tareas" | Client-side filter on `responsible IN ('cliente', 'mixto')` | NO backend query change · UI toggle simple |
| SSE emit | Admin POST/PATCH plan endpoints emit `m17.plan.updated` best-effort | Pattern Phase 1A+1B+1C+1D sostained |
| Sidebar nav | Add "Mi plan" entry section "Mi empresa" | Consistent placement with Phase 1C "Conexiones cloud" |

---

## ETA cumulative refined

Phase 1E.1 backend endpoint + tests + SSE emit: ~1h
Phase 1E.2 refactor PlanGantt + cliente page + lib API + sidebar: ~1.5h
Phase 1E.3 E2E spec: ~30 min
**Total**: ~3h refined vs ~3-5h briefing nominal · OPS-045 51ª manifestation -20% to -40%.

## Patterns reusables Phase 1E

- ✅ Sub-atom 5.A audit_log 3-way OR (project_id + client_id)
- ✅ ClientSseEventType extend (`m17.plan.updated` added)
- ✅ subscribe-refetch pattern (useClientProjectEvents + tanstack invalidateQueries)
- ✅ ADR-025 reuse infrastructure (PlanGantt GanttView export · NO duplicación)
- ✅ best-effort SSE emit try/except logger.exception
- ✅ R29 friendly + R30 inverso (cliente NO admin lingo)
- ✅ ADR-013 doble pool (require_client_user)
- ✅ Pure functional adaptive (export GanttView · accepts data prop)
