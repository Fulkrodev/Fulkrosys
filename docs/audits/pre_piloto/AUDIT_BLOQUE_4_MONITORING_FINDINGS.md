# AUDIT Bloque 4 Phase 0 · Monitoring multi-tenant empirical state

**Status**: ✅ Phase 0 empirical complete · scope-clarification CRÍTICA detectada
**Date**: 2026-05-24 (post-marathon Bloque 3+5 day · siguiente sesión)
**HEAD base**: faab45f (post Bloque 3+5 cierre)
**Methodology**: find/cat/wc/head/tail/ls (NO grep) · OPS-052 strengthened doctrine

---

## Verdict empírico · scope CLARIFICATION crítica

`m_compliance_monitor` (3103 LOC) es **GLOBAL FULKRO platform self-monitoring** · **NO per-project multi-tenant**. Briefing nominal asume "multi-tenant per-project" pero realidad arquitectural es:

- **m_compliance_monitor** · 19 checks autónomos · 6 normas (RGPD · LOPDGDD · LSSI-CE · NIS2 · ISO 27001 · ENS) · scope **FULKRO platform self-monitoring** · NO cliente-data · admin/internal
- **Per-project cliente compliance** vive en otros motores: M27 conformity · M04 plan adecuación · M03 DdA · M07 evidence vault · etc
- **Trust Center público** vía `/legal/trust` public_api existing (NO auth · agregada FULKRO health solamente)

**Gap real refined Phase 0**:
1. **Cliente compliance feed AGGREGATOR** · cliente portal page NEW que aggregate per-project compliance status desde M27 + M04 + M07 + cloud remediations + tasks pending (NO consume m_compliance_monitor · cliente NO ve self-monitoring FULKRO interno)
2. **Admin cross-project compliance dashboard** · admin NEW page que muestra TODAS proyectos cliente compliance posture aggregated (similar pattern Action Plans cross-motor existing en /admin/projects/[id]/planes-accion)
3. **System-health propio FULKRO** · m_compliance_monitor + m_observability existing combined dashboard

**ETA empírico realista refined**: ~3-5h (vs ~5-8h briefing nominal · ahorro ~30-40% per scope clarification + OPS-045 reuse infrastructure):
- Phase A cliente compliance feed aggregator · ~1.5-2h (reuse existing M27/M04 endpoints)
- Phase B admin cross-project dashboard · ~1.5-2h (reuse existing data + new aggregator endpoint)
- Phase C alerts dispatch wire · scope-out absorbido (m18 alerts service existing + 1.D.G EXPANDED SSE)
- Phase D system-health propio dashboard · ~30-45 min (admin internal · reuse m_compliance_monitor existing)
- Phase E cierre · ~30 min

---

## Stats baseline existing 100% leveraged

### m_compliance_monitor (3103 LOC · global self-monitoring FULKRO)
- `checks.py` 1057 LOC · 19 named checks CHECK_REGISTRY (17 base atom 9.bis.6 + 2 atom 10.1)
- `service.py` 475 LOC · `ComplianceMonitorService` orchestrates check runs + alert lifecycle + email digest
- `public_api.py` 325 LOC · `/legal/trust` public · agregada FULKRO health (NO auth)
- `norma_reports_service.py` 278 LOC · per-norma reports generation
- `api.py` 230 LOC · `/admin/compliance/monitor/*` admin endpoints
- `reports_service.py` 210 LOC · reports
- `norma_reports_api.py` 195 LOC · `/admin/compliance/norma-reports/*`
- `tasks.py` 94 LOC · Celery beat scheduled (daily 07:30 · weekly Mon 08:00 · monthly 1st · quarterly)
- `normas/` 7 plugin modules (registry pattern · 6 normas + base)
- `schemas.py` 94 LOC · Pydantic in/out

### m_observability (2093 LOC · LLM cost + transparency + golden eval)
- `eval_runner.py` 472 LOC · golden eval pipeline
- `llm_observability_service.py` 371 LOC · LLM cost tracking + anomaly alerts
- `models.py` 259 LOC · ORM
- `golden_eval_runs_service.py` 213 LOC
- `transparency_service.py` 182 LOC · AI Act compliance
- `api.py` 126 LOC · admin endpoints `/admin/llm-observability/*`
- `golden_eval_runs_api.py` 109 LOC · `/admin/llm-observability/golden-eval/*`
- `transparency_api.py` 104 LOC
- `tasks.py` 56 LOC · Celery scheduled background

### Frontend existing admin
- `/admin/compliance/monitor/page.tsx` 494 LOC · self-monitoring dashboard (17 checks · alerts table · reports)
- `/admin/compliance/norma-reports/page.tsx` 237 LOC · per-norma reports list
- `/admin/llm-observability/page.tsx` · LLM cost dashboard
- `/admin/llm-observability/golden-eval/page.tsx` · golden eval runs

### Frontend existing cliente
- `/client-portal/conformidad/page.tsx` 148 LOC · M27 conformity status (per-project)
- `/client-portal/dpc-anual/page.tsx` · DPC anual
- `/client-portal/dda/page.tsx` · DdA review
- `/client-portal/policies/page.tsx` · políticas
- `/client-portal/remediaciones/page.tsx` · cloud remediations (Bloque 3+5 just-created)

### Alerts infrastructure (existing)
- `m18_communication/alert_service.py` · alert service
- `m18_communication/alerts_api.py` · REST endpoints
- 13 notification templates YAML
- `/admin/alerts/page.tsx` existing
- `frontend/components/alerts/AlertBell.tsx` existing
- SSE dispatcher audience-aware (1.D.G EXPANDED)
- NotificationOrchestrator 427 LOC

### Multi-tenant scope verification
- `m_compliance_monitor` NO per-project scope (global FULKRO)
- Per-project compliance vive en M27 (conformity) + M04 (plan) + M03 (DdA) + M07 (evidence)
- `/legal/trust` public_api · global FULKRO posture (NO per-cliente)

---

## Gap matrix refined Phase 0

| Gap | Scope realista | Phase | ETA |
|-----|----------------|-------|-----|
| Cliente compliance feed AGGREGATOR (M27+M04+M07+cloud remediations+tasks pending) | NEW page cliente reuse 4 endpoints existing | A | ~1.5-2h |
| Admin cross-project compliance dashboard aggregated | NEW page admin + 1 aggregator endpoint backend | B | ~1.5-2h |
| Alerts dispatch wire compliance failure → cliente notification | EXTEND m_compliance_monitor service alert_lifecycle | C | scope-out absorbido (infra existing) |
| System-health propio FULKRO combined dashboard | NEW page admin reuse m_compliance_monitor + m_observability data | D | ~30-45 min |
| E2E validation + CLAUDE.md cierre | docs | E | ~30 min |

**Total**: **~3-5h cumulative empírico** (vs ~5-8h nominal · ahorro ~30-40% sostained pattern OPS-045 52ª aplicación)

---

## Scope-out decisions documented

### Phase C alerts dispatch · ABSORBIDO infra existing
- m18_communication alerts service production
- 13 notification templates YAML existing
- SSE dispatcher audience-aware (1.D.G EXPANDED)
- NotificationOrchestrator 427 LOC
- `/admin/alerts/page.tsx` + AlertBell component existing
- **NO new alert infrastructure needed** · solo wire compliance failure events a alerts existing si gap real detectado

### Multi-tenant per-project m_compliance_monitor · scope-out CLARIFY
- m_compliance_monitor es SELF-MONITORING FULKRO global (admin-only)
- Per-cliente compliance vía OTROS motores (M27/M04/M03/M07)
- NO refactor m_compliance_monitor para per-project scope
- Aggregator pattern reuse · NO new tables

---

## OPS-052 12ª manifestation NOT TRIGGERED

| Criterio | Resultado Phase 0 |
|----------|-------------------|
| Briefing-vs-reality mismatch >30% | 🟡 PARTIAL (multi-tenant assumption wrong · scope refined) |
| Scope inflation >50% | ❌ NO (~3-5h refined vs ~5-8h nominal · ahorro 30-40%) |
| Existing infrastructure hidden invalida plan | 🟡 PARTIAL (m_compliance_monitor scope clarified · alerts infra absorbed C) |

**Decision**: 12ª OPS-052 borderline · scope-clarify es honest path · proceed Phase A con scope-adjusted ETA.

---

## Implementation plan refined Phase A → E

### Phase A · Cliente compliance feed aggregator (~1.5-2h · 2 commits)
- A.1: lib/api/cliente/compliance-summary.ts + hook useClienteComplianceSummary (~30 min)
- A.2: page `/client-portal/cumplimiento/page.tsx` + ComplianceSummaryCard components + sidebar entry (~1-1.5h)
- Reuse 4 endpoints existing:
  - M27 conformity readiness (`/portal/conformidad/*`)
  - M04 plan adecuación status (via portal_workflow)
  - M07 evidencias count
  - Cloud remediations count (Bloque 3+5 just-created `/client-portal/cloud-gaps`)

### Phase B · Admin cross-project compliance dashboard (~1.5-2h · 2 commits)
- B.1: backend `cross_project_compliance_aggregator.py` service + endpoint (~45 min)
- B.2: frontend `/admin/cross-project-compliance/page.tsx` + AggregatedTable + Heatmap (~1-1.5h)
- Reuse OPS-045 audit-first pattern · query agregada multi-project sin nuevas tablas

### Phase C · Alerts dispatch · SCOPE-OUT ABSORBIDO
- Pattern existing m18 + 1.D.G EXPANDED suficiente
- NO new alerts infrastructure
- Wire compliance check failure → existing alert service si gap detectado durante Phase A/B implementation

### Phase D · System-health propio FULKRO (~30-45 min · 1 commit)
- NEW `/admin/system-health/page.tsx` dashboard combinado:
  - 19 checks m_compliance_monitor latest status
  - LLM provider availability m_observability
  - DB pool health (reuse existing infra si disponible · sino stub)
  - Disk usage Hetzner (DEFER post-FASE-1.F production)
- Tests scope-light (2-3 unit · render verification)

### Phase E · Validation + CLAUDE.md cierre (~30 min · 1 commit)
- VALIDATION_BLOQUE_4_MONITORING.md document
- CLAUDE.md sub-atom Bloque 4 CERRADO section
- Future polish capture

**Total**: ~3-5h cumulative · 6 commits

---

## Cross-ref

- m_compliance_monitor source: `backend/app/motors/m_compliance_monitor/`
- m_observability source: `backend/app/motors/m_observability/`
- M27 conformity: `backend/app/motors/m27_conformity/`
- M18 alerts: `backend/app/motors/m18_communication/`
- Bloque 3+5 cloud remediations: `backend/app/motors/m_cloud_connectors/remediation_orchestrator.py`
- SSE dispatcher: `backend/app/core/sse_dispatcher.py`
- ADR-013 doble pool · ADR-031 ENAC trazabilidad · OPS-045 audit-first

---

## Honest notes

1. Briefing nominal "multi-tenant per-project" assumption empíricamente NO match m_compliance_monitor scope (global self-monitoring) · scope refined honestly Phase A focus aggregator pattern
2. M27 conformity readiness endpoint existing cliente-facing · reuse 100% Phase A
3. Cloud remediations Bloque 3+5 just-created · aggregator includes count automáticamente
4. Phase C alerts scope-out absorbed · si gap real detected durante implementation re-evaluate
5. System-health propio Phase D admin internal scope · cliente NO ve (R29 sostained · self-monitoring NO cliente concern)
