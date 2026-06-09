# AUDIT CLUSTER 2 Phase 2B · AuditLog → ClientNotification Wire Empirical State

**Sesión**: 3B-2B.8 CLUSTER 2 Path B Phase 2B
**Fecha**: 2026-05-26
**Ejecutor**: Phase 2B.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined small + high-value · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 2B asumió necesidad de NEW centralized router AuditLog→NotificationOrchestrator + bridge accion names `admin.evidence.rejected` / `admin.document.approved` / `workflow.phase.transitioned` / `cliente.signature.requested`. Empirical reality:

- ✅ **NotificationOrchestrator EXISTS** ([orchestrator.py](../../backend/app/notifications/orchestrator.py) · ADR-039 MB-16.2 · 12 motor_adapters)
- ✅ **emit_client_notification service EXISTS** ([notification_service.py](../../backend/app/motors/m21_portal_cliente/notification_service.py) · 17 VALID_TYPES enum + in-app inbox)
- ✅ **Cliente inbox API + UI EXIST** (`/api/v1/portal/inbox` + `/client-portal/inbox/page.tsx`)
- ✅ **6 motors ya wired ClientNotification empirical** (m05 + m25 + m_cloud_connectors digest + system_consciousness + m09 dda_evidence_gap)
- ❌ **Briefing accion names `admin.evidence.rejected`/etc NOT exist** en codebase (PROSPECTIVE events · NO emit empirical hoy)
- ❌ **CLUSTER 1 admin actions NOT wired notification cliente**:
  - Phase 1A `m01.categorizacion.completed` (admin firma acta · cliente NO recibe notif)
  - Phase 1B `m02.magerit.updated` (admin congela analysis · cliente NO recibe notif)
  - Phase 1E `m17.plan.updated` (admin PATCH task · cliente NO recibe notif)

**Filosofía cliente-mínimo guard**: 3 CLUSTER 1 admin-actions identified como cliente-action-surfacing (cliente RECIBE update · NO ejecuta admin operation). 100% aligned · 0 violations.

ETA refined: ~1.5h vs briefing 2-3h nominal (-25% to -50% OPS-045 53ª manifestation · scope refined a wire-completeness gap-fix vs greenfield centralized router).

---

## Phase 2B.0.1 · NotificationOrchestrator + ClientNotification service empirical

### NotificationOrchestrator (ADR-039 MB-16.2)
- **Path**: [backend/app/notifications/orchestrator.py](../../backend/app/notifications/orchestrator.py)
- **API**: `enqueue()` + `enqueue_with_template()` · DispatchOutcome return
- **Channels**: email + portal_sse + whatsapp (3 canales)
- **Features**: DND-aware + template resolver YAML + preferences per-user + SSE dispatch coupling
- **Motor adapters**: 12 funciones existentes (notify_chat_admin_reply · notify_task_assigned · notify_evidence_expiring · notify_phase_changed · notify_audit_due · notify_milestone_billed · notify_payment_received · notify_signoff_completed · notify_incident_resolved_cliente · notify_evidence_quarantined_admin · notify_retainer_quarterly_signed · notify_acta_signed)

### emit_client_notification service (ADR-020 v3)
- **Path**: [backend/app/motors/m21_portal_cliente/notification_service.py](../../backend/app/motors/m21_portal_cliente/notification_service.py)
- **API**: `emit_client_notification(db, project_id, client_user_id, type, title, body, target_url, priority, payload, emitted_by_motor)`
- **VALID_TYPES** (17): evidence_request, acta_review, retainer_offer, retainer_reconsideration, onboarding_ready, generic_alert, invoice_review, risk_validation, compliance_confirmation, meeting_invite, scope_change_validation, incident_report, nps_survey, vote_request, **report_available**, renewal_campaign, info_request
- **VALID_PRIORITIES** (4): low, normal, high, urgent
- **Storage**: in-app inbox only (ClientNotification model · SAN-E v3.MB-4.bis3)
- **NO email/SSE dispatch direct** (in-app polling + manual subscribe via inbox API)

### Existing wires (6 motors)
| Motor | File | Event types emitted |
|-------|------|---------------------|
| m05_obligations | api.py:334 | obligation due notifications |
| m25_lifecycle | lifecycle_paso4.py:369, 684 | retainer_offer + retainer_reconsideration |
| m_cloud_connectors | digest_service.py:242 | report_available (monthly digest) |
| m_cloud_connectors | system_consciousness_hooks.py:347 | generic_alert |
| m09_audit_prep | dda_evidence_gap_api.py:204 | info_request (Marcos requesting more evidence) |

---

## Phase 2B.0.2 · CLUSTER 1 audit_log accion strings empirical map

| Accion | Source motor | Cliente notification needed? | Filosofía cliente-mínimo aligned? |
|--------|--------------|------------------------------|-----------------------------------|
| `cliente.cloud_connector.viewed` | Phase 1C api_cliente.py | NO (own action GET) | ✅ |
| `cliente.cloud_connector.connect_initiated` | Phase 1C | NO (own action POST) | ✅ |
| `cliente.cloud_connector.disconnect_requested` | Phase 1C | NO (own action POST · already chat-mediated msg sent) | ✅ |
| `cliente.categorizacion.viewed` | Phase 1A m21 | NO (own action GET) | ✅ |
| `cliente.magerit.viewed` | Phase 1B m02 portal_api | NO (own action GET) | ✅ |
| `cliente.plan.viewed` | Phase 1E m17 portal_api | NO (own action GET) | ✅ |
| `copilot.hint.generated` (admin) | Phase 1D m11 api | NO (UI flow internal) | n/a admin |
| `copilot.hint.generated` (cliente) | Phase 1D m11 portal_api | NO (UI flow internal) | ✅ |
| **`m01.categorizacion.completed`** (admin SSE event) | Phase 1A m01 api | **YES** (admin done · cliente recibe "Marcos terminó · revísalo") | ✅ |
| **`m02.magerit.updated`** (admin SSE event) | Phase 1B m02 api | **YES** (admin congelado · cliente recibe "MAGERIT lista") | ✅ |
| **`m17.plan.updated`** (admin SSE event) | Phase 1E m17 api | **YES** (admin actualizó · cliente recibe "Plan actualizado") | ✅ |

**Gap identified**: 3 admin-action SSE events NOT wired ClientNotification cliente inbox.

---

## Phase 2B.0.3 · Briefing accion names check empirical

| Briefing accion | Empirical exists? | Action |
|-----------------|-------------------|--------|
| `cliente.action.required.*` | NOT pattern in codebase | DEFER Future-X (architectural namespace future) |
| `admin.evidence.rejected` | NOT emit currently | DEFER · CLUSTER 3+ evidence reject flow scope |
| `admin.document.approved` | NOT emit currently | DEFER · CLUSTER 3+ document signoff flow |
| `workflow.phase.transitioned` | Phase changes via `tg_projects_phase_changed` trigger en `project_lifecycle_events` (NOT audit_log table) | DEFER · separate notification path |
| `cliente.signature.requested` | NOT emit · signature requests via magic_link M12 flow | DEFER · M12 magic-link path |

**Conclusion**: briefing accion names son PROSPECTIVE · NO emit empirical hoy en codebase. Wire futuro cuando esos events sean emitidos por motors específicos (CLUSTER 3+ scope).

---

## Phase 2B.0.4 · Recommended Phase 2B refined scope (~1.5h)

### Phase 2B.1 implementation (~45-60 min)

Add ClientNotification emit en 3 motor endpoints CLUSTER 1 admin actions (best-effort try/except pattern Phase 1A+1B+1C+1D+1E sostained):

1. **m01_categorization/api.py** finalize categorización endpoint:
   - Post SSE dispatch `m01.categorizacion.completed`
   - ADD: `emit_client_notification` con type=`compliance_confirmation`, title="Marcos finalizó tu categorización ENS", body, target_url=`/client-portal/categorizacion`, priority=`normal`
   - Lookup client_user_id per project (cliente single-user pilot assumption)

2. **m02_magerit/api.py** save analysis endpoint:
   - Post SSE dispatch `m02.magerit.updated`
   - ADD: `emit_client_notification` con type=`compliance_confirmation`, title="Marcos actualizó tu análisis MAGERIT", body, target_url=`/client-portal/magerit`, priority=`normal`

3. **m17_planning/api.py** update_task endpoint:
   - Post SSE dispatch `m17.plan.updated`
   - ADD: `emit_client_notification` con type=`generic_alert`, title="Plan ENS actualizado", body=f"Marcos actualizó {task_name}", target_url=`/client-portal/plan`, priority=`low`

### Phase 2B.2 tests (~30-45 min)

Backend tests (3-5 tests):
- Test m01 finalize categorización → ClientNotification row created cliente inbox
- Test m02 save MAGERIT analysis → ClientNotification row created
- Test m17 update task → ClientNotification row created
- Test ClientNotification respects cliente_id ownership (RLS · Sub-atom 5.A)
- Test SSE dispatch coexists with notification emit (best-effort independent)

### Phase 2B.3 audit_log forward-compat (DEFER scope)

Briefing requested `cliente.notification.dispatched` audit_log emit on dispatch:
- DEFER Future-1.E.X.notification-dispatch-audit-log (~30 min · low priority · in-app inbox itself acts as audit trail via ClientNotification.created_at + read_at)

---

## ETA refined Phase 2B

- **Briefing nominal**: ~2-3h
- **Empirical refined**: ~1.5h (wire-completeness gap-fix · 3 endpoints additive · NO new infrastructure)
- **OPS-045 53ª manifestation**: -25% to -50% vs nominal (audit-first reveals 6 motors ya wired + infrastructure complete)

---

## Filosofía cliente-mínimo compliance

3 nuevos notifications wires evaluadas:
- m01.categorizacion.completed → cliente RECIBE "categorización lista revísala" · ✅ aligned
- m02.magerit.updated → cliente RECIBE "MAGERIT actualizada" · ✅ aligned
- m17.plan.updated → cliente RECIBE "plan actualizado" · ✅ aligned

**ZERO admin-internal operations leaked cliente**. All notifications son cliente VE/RECIBE pattern.

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing scope intent (AuditLog → NotificationOrchestrator wire cliente-relevant) ratified · refined a empirical gap-fix scope concrete (3 CLUSTER 1 events vs greenfield assumption centralized router).

PROSPECTIVE briefing accion names (`admin.evidence.rejected` · `cliente.signature.requested` · etc.) DEFER Future-X cuando emit empirical existe (CLUSTER 3+ scope).

---

## Patterns potencialmente formalizables Phase 2B

- **SSE + ClientNotification dual emit pattern** (admin action triggers BOTH realtime SSE + persistent inbox notification · best-effort independent · graceful degradation single channel fails)
- **Cliente notification type taxonomy gap-fill** (compliance_confirmation + generic_alert + report_available · existing VALID_TYPES adequate · NO new types needed Phase 2B)

---

## Decisión pendiente

⏸️ **Architect approve Phase 2B.1 refined scope**:
- Wire 3 CLUSTER 1 admin-action endpoints (m01 + m02 + m17) emit ClientNotification cliente inbox
- best-effort try/except pattern post SSE dispatch
- 3-5 backend tests + cliente_id RLS verification
- DEFER prospective briefing accion names Future-X (CLUSTER 3+ emit empirical)
- ETA refined ~1.5h
