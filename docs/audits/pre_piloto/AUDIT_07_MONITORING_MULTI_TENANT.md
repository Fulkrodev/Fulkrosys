# AUDIT #8 · Monitoreo continuo multi-cliente + propio 24/7

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 7/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #8 · "Monitoreo continuo multi-cliente (per-project alerts) + monitoreo propio plataforma 24/7"

---

## Verdict empírico

Infrastructure monitoring **MASSIVE production-grade** dual:
- **m_observability** (~2093 LOC): LLM cost monitoring + golden eval runs + transparency tracking
- **m_compliance_monitor** (~3084 LOC per Audit #2): **19 named checks** (17 base + 2 ENS/RGPD) + 17 tests verified
- **m18_communication** alerts_api + alert_service · sistema alertas dedicated

**Gap específico identificado**: 
- Multi-tenant monitoring **per-project alerts** scope NOT verified (probable global FULKRO-level only · cliente-scoped alerts wire UI cliente gap)
- Cliente-side compliance alerts visibility gap (per Audit #4 · `/inbox` genérico · NO dedicated alerts feed)

**ETA empírico realista refined**: ~3-6h wire UI cliente compliance feed + per-project scope verify (vs ~10-15h nominal greenfield assumed)

---

## Stats baseline

### m_observability (~2093 LOC · LLM observability + transparency)
- `eval_runner.py` 472 LOC · golden eval pipeline
- `llm_observability_service.py` 371 LOC · LLM cost tracking
- `models.py` 259 LOC · ORM
- `golden_eval_runs_service.py` 213 LOC
- `transparency_service.py` 182 LOC · transparency report
- `api.py` 126 LOC + `golden_eval_runs_api.py` 109 LOC + `transparency_api.py` 104 LOC
- `tasks.py` 56 LOC · Celery
- `evaluators/` directory · evaluation suite

### m_compliance_monitor (per Audit #2 · 5790 LOC cumulative)
- **CHECK_REGISTRY 19 checks** (17 base atom 9.bis.6 + 2 atom 10.1)
- Beat schedule cadences:
  - daily 07:30 Europe/Madrid
  - weekly Mon 08:00
  - monthly 1st 08:30
  - quarterly 1st Jan/Apr/Jul/Oct 09:00
- Result statuses: green/yellow/red/unknown
- `consecutive_failures` triggers yellow alert after 3 in a row
- 75 tests verified existing (per memoria)

### m18_communication alerts (~3 files)
- `alert_service.py` core service
- `alerts_api.py` REST endpoints
- `alert_schemas.py` Pydantic in/out

### Notifications templates (~13 YAML existing)
- audit_due · evidence_expiring · evidence_quarantined_admin · incident_resolved_cliente · milestone_billed · payment_received · phase_changed · acta_signed · chat_admin_reply · client_inactivity_admin · retainer_quarterly_signed · signoff_completed · task_assigned

---

## Multi-tenant scope analysis

### Per-project alerts existing
- m18_communication alerts_api · scope NOT verified per-project explicit
- Templates above incluyen multi-tenant capable (e.g. `evidence_expiring` triggers per-project evidence)
- Notification orchestrator (Phase 0 1.E.2.bis · ya existing audit confirmed)

### Cliente portal alerts visibility (gap per Audit #4)
- `/client-portal/inbox` genérico (cliente notifications inbox)
- `/client-portal/incidents` specific (incident management)
- NO dedicated `/client-portal/alerts/compliance` feed per-project alerts
- **Wire gap**: m_compliance_monitor 19 checks running but cliente NO visibility per-project compliance posture

### FULKRO self-monitoring 24/7
- m_observability + m_compliance_monitor cubre self-monitoring
- 19 checks beat schedule auto-runs
- Admin dashboard `/admin/compliance/monitor` (494 LOC) visible status + alerts table

---

## Gap matrix

| Capability | Backend | Frontend | Status |
|-----------|---------|----------|--------|
| FULKRO self-monitoring 24/7 | ✅ m_compliance_monitor 19 checks | ✅ /admin/compliance/monitor | DONE |
| LLM cost + transparency tracking | ✅ m_observability | ✅ /admin/llm-observability | DONE |
| Per-project alerts orchestration | ✅ alert_service · templates 13 | 🟡 PARTIAL · solo /inbox | MEDIUM gap |
| Cliente per-project compliance feed | 🟡 m_compliance_monitor scope GLOBAL · per-project verify needed | 🔴 MISSING · /client-portal/alerts/compliance | HIGH gap |
| Hetzner infrastructure monitoring | 🔴 NOT integrated yet | 🔴 N/A | Future-1.F deploy |

---

## Recomendación

**Pre-piloto MEDIA scope**:
1. **MEDIUM** (~2-3h): Verify m_compliance_monitor 19 checks `project_id` scope OR refactor to multi-tenant if global only · backend audit only
2. **HIGH** (~3-5h): Wire cliente `/client-portal/alerts/compliance` page · feed from m_compliance_monitor + per-project alert filter · reuse m18 alerts API existing
3. **POST-PILOTO** (~4-6h): Hetzner infrastructure monitoring integration (Prometheus + Grafana basic setup · FASE 1.F natural)

**Total pre-piloto**: ~5-8h scope refined empírico (vs ~10-15h nominal · audit-first reveals infrastructure massive ready · solo wire UI cliente missing)

---

## Cross-ref

- m_observability source: `backend/app/motors/m_observability/`
- m_compliance_monitor source: `backend/app/motors/m_compliance_monitor/` + checks.py 1057 LOC (19 checks per docstring)
- m18 alerts: `backend/app/motors/m18_communication/alert*.py`
- Notification templates: `backend/app/notifications/templates/`
- Admin dashboards: `/admin/compliance/monitor` + `/admin/llm-observability`
- Audit #4 cross-reference cliente portal gap

---

## Honest notes

1. NO inspección detallada per-project scope CHECK_REGISTRY (audit demand-driven cuando wire cliente)
2. Hetzner monitoring integration es FASE 1.F natural (deploy includes basic monitoring setup)
3. Wire `/client-portal/alerts/compliance` feed reusa m18 alerts API existing · NO greenfield backend
