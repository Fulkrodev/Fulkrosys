# AUDIT CLUSTER 2 Phase 2A · SSE Channels + CLIENTE_EVENT_TYPES Filter Completeness

**Sesión**: 3B-2B.8 CLUSTER 2 Path B Phase 2A
**Fecha**: 2026-05-26
**Ejecutor**: Phase 2A.0 OPS-052 micro-audit mandatory (architect firmísimo doctrine)
**Status**: 🛑 **CRITICAL BUG SCOPE confirmed** · 12 cliente-relevant events NOT en CLIENTE_EVENT_TYPES whitelist · audience filter empirical BLOCKS · Phase 1C + Phase 1E SSE functionally broken cliente-side

---

## Resumen ejecutivo

Phase 2A.0 audit empirical reveló **critical bug pre-existing**: backend audience filter `event_matches_audience` ([backend/app/core/sse_dispatcher.py:121](../../backend/app/core/sse_dispatcher.py#L121)) bloquea 12 eventos cliente-relevantes via `if event_type not in CLIENTE_EVENT_TYPES: return False` (línea 141).

**Implicación empírica**:
- Phase 1A + 1B sync ✅ (events m01/m02 whitelist)
- Phase 1C `cloud.connector.disconnect_requested` ✅ backend emit pero cliente NUNCA recibe (audience BLOCKED)
- Phase 1E `m17.plan.updated` ✅ backend emit pero cliente NUNCA recibe (audience BLOCKED)
- Bloque 3+5 `cloud_remediation_*` (9 events) ❌ cliente UI usa via tanstack invalidate fallback (no via SSE realtime)
- M21 chat `chat_message_new` ❌ cliente NO recibe nuevos mensajes admin via SSE realtime

**Phase 2A scope refined**: extend `CLIENTE_EVENT_TYPES` whitelist + add audience filter logic per event type semantics + add backend tests cliente whitelist coverage + verify Phase 1C + 1E SSE empirical end-to-end.

ETA refined: ~2h (bug fix scope vs ~2-3h briefing nominal · NO new feature work).

---

## Phase 2A.0.1 · SSE emit points cross-motor empirical (11 motors)

**Total SSE emit points discovered grep `sse_dispatcher.dispatch`**: 11 distinct motor sources · ~15 unique event types.

| # | Source motor | Event type emitted | Cliente relevant? | In CLIENTE_EVENT_TYPES? |
|---|--------------|---------------------|-------------------|--------------------------|
| 1 | m_workflow_engine/dependency_resolver_service.py | `step_completed` | YES (cliente sees admin terminó step) | ✅ |
| 2 | m_workflow_engine/dependency_resolver_service.py | `step_unblocked` | YES (cliente sees own next action) | ✅ |
| 3 | m_workflow_engine/dependency_resolver_service.py | `step_blocked` | YES | ✅ |
| 4 | m18_communication/alert_service.py | `alert_new` | NO (admin internal) | NO (correctly excluded) |
| 5 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_proposed` | YES (cliente `/remediaciones` UI) | ❌ **MISSING** |
| 6 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_approved` | YES | ❌ **MISSING** |
| 7 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_rejected` | YES | ❌ **MISSING** |
| 8 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_executing` | YES | ❌ **MISSING** |
| 9 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_executed` | YES (success notification) | ❌ **MISSING** |
| 10 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_failed` | YES | ❌ **MISSING** |
| 11 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_verification_pending` | YES | ❌ **MISSING** |
| 12 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_verified` | YES | ❌ **MISSING** |
| 13 | m_cloud_connectors/remediation_orchestrator.py | `cloud_remediation_rollback_requested` | YES | ❌ **MISSING** |
| 14 | m_cloud_connectors/api_cliente.py (Phase 1C) | `cloud.connector.disconnect_requested` | YES (cliente echo own request) | ❌ **MISSING** |
| 15 | m_cloud_connectors/system_consciousness_hooks.py | `compliance_dashboard_refresh_required` | NO (admin internal) | NO (correctly excluded) |
| 16 | m_cloud_connectors/system_consciousness_hooks.py | `cross_project_compliance_refresh_required` | NO (admin internal cross-project) | NO (correctly excluded) |
| 17 | m21_portal_cliente/chat_service.py | `chat_message_new` | YES (cliente sees new admin message realtime) | ❌ **MISSING** |
| 18 | m08_verification/pentest_auto_trigger_events.py | `pentest_check_required` | YES (cliente ALTA pentest authorization step) | ❌ **MISSING** |
| 19 | m09_audit_prep/auditor_clarifications_api.py | `auditor_clarification_new` | NO (auditor portal scope · separate magic-link auth) | NO (correctly excluded) |
| 20 | m17_planning/api.py (Phase 1E) | `m17.plan.updated` | YES (cliente sees plan task change) | ❌ **MISSING** |
| 21 | m01_categorization/api.py (Phase 1A) | `m01.categorizacion.completed` | YES (cliente sync) | ✅ |
| 22 | m02_magerit/api.py (Phase 1B) | `m02.magerit.updated` | YES (cliente sync) | ✅ |

**Summary**:
- **6 events in CLIENTE_EVENT_TYPES** (step_completed/unblocked/blocked + m01.categorizacion.completed + m02.magerit.updated · NO 6th explicit count = 5 actually)
- **4 events correctly excluded** (alert_new + compliance refresh internal + auditor_clarification)
- **12 events MISSING from CLIENTE_EVENT_TYPES** · cliente UI subscribes pero backend BLOCKS

---

## Phase 2A.0.2 · audience filter semantic gaps

`event_matches_audience` ([sse_dispatcher.py:121-156](../../backend/app/core/sse_dispatcher.py#L121-L156)) tiene logic per event type pero:

- ✅ `step_completed/m01.categorizacion.completed/m02.magerit.updated` requieren `primary_actor=admin` (cliente sees admin done X)
- ✅ `step_unblocked/step_blocked` requieren `primary_actor=cliente` (cliente sees own action needed)
- ❌ **NO logic for 12 missing events** · simply blocked by whitelist check at línea 141

---

## Phase 2A.0.3 · Frontend impact empirical

**Phase 1C `/cloud-connections` page**:
- [frontend/hooks/useClientProjectEvents.ts](../../frontend/hooks/useClientProjectEvents.ts) lines 273-289 register listeners for 5 `cloud.connector.*` events
- Backend emits ✅ pero `EventSource` cliente connection RECIBE filtered set
- **Empirical**: cliente UI Phase 1C disconnect_requested NUNCA actualizada realtime (relies on toast post-mutation Phase 1C local optimistic)

**Phase 1E `/plan` page**:
- useClientProjectEvents extend `onM17PlanUpdated` handler
- Backend emits on admin PATCH task ✅
- **Empirical**: cliente UI NUNCA receives plan update toast realtime · tanstack staleTime 60s fallback only

**Bloque 3+5 `/remediaciones` page**:
- [frontend/app/(client-portal)/client-portal/remediaciones/page.tsx](../../frontend/app/(client-portal)/client-portal/remediaciones/page.tsx) usa useClientProjectEvents con `invalidateQueries` pattern
- **Empirical**: tanstack invalidate fallback funciona post-cliente-mutation pero NO real-time updates cuando ADMIN ejecuta remediation

**M21 chat**:
- Cliente chat UI · cliente NO recibe nuevos mensajes admin via SSE realtime · solo polling tanstack staleTime

---

## Phase 2A.0.4 · Filosofía cliente-mínimo compliance per event

Per architect CLUSTER 1 retrospective: "cliente VE/AUTORIZA/FIRMA/RECIBE · NO opera ENS implementation técnica".

| Event type | Cliente acción/percepción | Filosofía cliente-mínimo aligned? |
|------------|---------------------------|-----------------------------------|
| cloud_remediation_proposed | RECIBE: "tienes propuesta" | ✅ aligned |
| cloud_remediation_approved | VE: own decision confirmed | ✅ aligned |
| cloud_remediation_executing | RECIBE: status update "Marcos aplicando" | ✅ aligned |
| cloud_remediation_executed | RECIBE: success toast | ✅ aligned |
| cloud_remediation_failed | RECIBE: status "Marcos revisará" R29 friendly | ✅ aligned |
| cloud.connector.disconnect_requested | VE: own request echo + Marcos ETA | ✅ aligned |
| m17.plan.updated | VE: plan timeline updated read-only | ✅ aligned |
| chat_message_new | RECIBE: new admin message notification | ✅ aligned |
| pentest_check_required | RECIBE: ALTA category authorization step pending | ✅ aligned (cliente solo autoriza ventana) |

**ZERO violations cliente-mínimo filosofía** · all 12 missing events aligned · 100% safe to add CLIENTE_EVENT_TYPES whitelist.

---

## Phase 2A.0.5 · Recommended scope refined Phase 2A

### Phase 2A.1 implementation (~1-1.5h)

1. **Extend CLIENTE_EVENT_TYPES whitelist** + 12 events (additive · NO breaking):
   ```python
   CLIENTE_EVENT_TYPES = frozenset({
       # Existing 5
       "step_completed", "step_unblocked", "step_blocked",
       "m01.categorizacion.completed", "m02.magerit.updated",
       # NEW Phase 2A · cumulative cliente-relevant events
       "m17.plan.updated",
       "cloud.connector.disconnect_requested",
       "chat_message_new",
       "pentest_check_required",
       "cloud_remediation_proposed", "cloud_remediation_approved",
       "cloud_remediation_rejected", "cloud_remediation_executing",
       "cloud_remediation_executed", "cloud_remediation_failed",
       "cloud_remediation_verification_pending",
       "cloud_remediation_verified",
       "cloud_remediation_rollback_requested",
   })
   ```

2. **Extend audience filter semantic logic** per event type cliente-mínimo guards:
   - `cloud_remediation_*` cuando `audience == "cliente"` (orchestrator emits con audience field empirical · verify per orchestrator)
   - `cloud.connector.disconnect_requested` always cliente (own request)
   - `chat_message_new` cuando `sender_type == "admin"` (cliente NO needs own echo)
   - `pentest_check_required` cuando ALTA category project (gate verified per project)
   - `m17.plan.updated` always cliente (admin updates task · cliente sees)

3. **NO frontend changes** required (Phase 1C + 1E + Bloque 3+5 hooks ALREADY subscribe correctly)

### Phase 2A.2 backend tests (~30-45 min)

- Test CLIENTE_EVENT_TYPES contains 17 events expected
- Test audience filter cliente accepts each new event with proper semantics
- Test audience filter cliente REJECTS internal events (alert_new + compliance refresh)
- Test Phase 1C disconnect_requested → cliente subscribes end-to-end empirical
- Test Phase 1E m17.plan.updated → cliente receives end-to-end empirical
- Test chat_message_new → cliente recibe cuando sender_type=admin (NO own echo)

### Phase 2A.3 audit_log emit (~15 min)

Per architect briefing "audit_log emit per event (R6 hash chain preserved)":
- Cada nuevo SSE event que reach cliente debe emit audit_log entry `cliente.sse.event_received` con event_type + project_id + client_id Sub-atom 5.A pattern (forward-compat · NO blocking)
- **DEFER Future-X**: backend-side audit_log on emit (admin actor side) ya cubierto por motor-specific audit_log emits (m01/m02/m17 etc) · NO necesario nuevo dispatcher-level emit per event

---

## ETA refined Phase 2A

- **Briefing nominal**: ~2-3h
- **Empirical refined**: ~1.5-2h (bug fix scope · NO new feature work · OPS-045 52ª manifestation)
- **Critical impact**: Phase 1C + Phase 1E SSE empirical wire-completeness CRITICAL pre-piloto cliente UX

---

## Patterns potencialmente formalizables Phase 2A

- **Audience whitelist + semantic filter pattern** (cumulative event_matches_audience) · architectural insurance preventing admin-internal events leak cliente
- **SSE wire-completeness audit empirical** (cross-motor grep + frontend hook listener match · ensure backend emit reaches cliente)

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario** · scope refined Phase 2A.1 sigue briefing intent (SSE wire-completeness) con concrete bug-fix scope discovered empirical. Briefing mismatch 0% (Phase 2A.0 audit ratifies briefing scope · solo refined a bug-fix implementation focus vs greenfield assumption).

---

## Decisión pendiente

⏸️ **Architect approve Phase 2A.1 refined scope**:
- Extend CLIENTE_EVENT_TYPES + 12 events
- Extend audience filter semantic logic
- Backend tests Phase 1C+1E end-to-end empirical
- audit_log forward-compat captured (DEFER Future-X audit-on-emit dispatcher-level)
- NO frontend changes (hooks ya subscribe correctamente)
- ETA refined ~1.5-2h
