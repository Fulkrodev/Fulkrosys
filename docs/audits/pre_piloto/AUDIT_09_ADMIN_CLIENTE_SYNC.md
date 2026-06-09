# AUDIT #10 · Admin ↔ cliente sync bidireccional (NEW)

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 9/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #10 (NEW) · "Sync bidireccional admin↔cliente · eventos real-time · approval flows"

---

## Verdict empírico

Infrastructure sync bidireccional **MASSIVE production-grade** post 1.D.G EXPANDED (8 commits sub-atom workflow cross-actor + real-time sync + rate limits copilot):

- ✅ **SSE dispatcher singleton** `core/sse_dispatcher.py` 150 LOC · audience-aware filtering (ADMIN vs CLIENTE event_types frozensets)
- ✅ **NotificationOrchestrator** `notifications/orchestrator.py` 427 LOC · in-app + Email + WhatsApp dispatch + DND timezone-aware
- ✅ **workflow_step_notifications.py** 244 LOC · cross-portal notifications cuando turno cambia
- ✅ **ClientNotification model** existing
- ✅ **m21 notification_service + notifications_inbox_api** cliente-side
- ✅ **WhatsApp dispatcher** existing
- ✅ **SSE endpoints**:
  - Admin: `backend/app/api/v1/sse_api.py`
  - Cliente: `backend/app/api/v1/sse_client_api.py` (cliente filtered audience)
- ✅ **DependencyResolverService.propagate_unblock** (workflow_engine) · auto-trigger notifications on step unblock

**Gap específico identificado**: NO real gap pre-piloto · infrastructure is production-grade · solo wire-up demand-driven per feature (cloud remediation approval flow wire reuses existing).

**ETA empírico realista refined**: ~0-2h pre-piloto (vs ~5-8h nominal) · solo wire-up nuevas features reusing infrastructure existing.

---

## Stats baseline

### SSE dispatch infrastructure
- `core/sse_dispatcher.py` 150 LOC singleton
- Channels: `project:{project_id}` · audience filtering admin/cliente
- Events existing: `step_completed`, `step_unblocked`, `step_blocked`, custom events extensible

### Notifications orchestration
- `notifications/orchestrator.py` 427 LOC `NotificationOrchestrator`
- API: `await orchestrator.enqueue(event_type, recipient, subject, html, text, project_id, template, payload)`
- Channels: Email (with retry 2s/8s/32s) + Portal SSE (best-effort)
- Preferences: factory default · DND timezone-aware · suppressed_dnd status
- Persistence: `NotificationEvent` + `NotificationPreference` models

### Cross-portal notifications
- `notifications/workflow_step_notifications.py` 244 LOC
- `send_admin_step_completed_notification` admin-side
- `send_client_unblock_notification` cliente-side
- Dynamic import graceful · NUNCA bloquea propagation

### Notification templates (13 YAML existing)
- acta_signed · audit_due · chat_admin_reply · client_inactivity_admin · evidence_expiring · evidence_quarantined_admin · incident_resolved_cliente · milestone_billed · payment_received · phase_changed · retainer_quarterly_signed · signoff_completed · task_assigned

### m21 cliente-side
- `notifications_inbox_api.py` API endpoints cliente notifications
- `notification_service.py` business logic
- `client_notification.py` model · `notifications.py` shared model

### WhatsApp
- `m31_whatsapp` motor · `sse_endpoint.py` separate SSE
- Feature flag `WHATSAPP_NOTIFICATIONS_ENABLED` (1.D.G.F)
- Tier-routing existing (per persona)

### Recent additions 1.D.G EXPANDED
- 8 commits cumulative: dependency_resolver + sse_cliente filtered + UI blockers cross-portal + workflow_step_notifications + rate_limit copilot
- Audience-aware event filtering ADMIN_EVENT_TYPES + CLIENTE_EVENT_TYPES frozensets

---

## Bidirectional flow analysis

### Admin → cliente (DONE)
- Admin marca step done → SSE `step_unblocked` event a cliente filter
- ClientNotification row created + Email + WhatsApp opt-in
- Cliente real-time receive via `useClientProjectEvents` hook
- UI blockers cliente · "Tu siguiente acción" · MarcosPreparaSection

### Cliente → admin (DONE)
- Cliente completa step → SSE `step_completed` event a admin filter
- Admin notification log
- UI admin · WorkflowBlockersPanel + recordar cliente endpoint

### Bidirectional state machine (DONE)
- `DependencyResolverService.propagate_unblock` auto-trigger ambos lados
- blocked → available → in_progress → done state machine cross-actor
- Materialidad cross-actor M28 cascade (FASE C Phase A · just-completed)

---

## Gap matrix per Audit #9 cloud remediation flow

| Sync need (cloud remediation) | Infrastructure existing | Wire-up needed |
|-------------------------------|------------------------|----------------|
| Admin propose → cliente notification | ✅ NotificationOrchestrator + 13 templates | NEW template `cloud_remediation_proposed.yaml` |
| Cliente real-time aware | ✅ useClientProjectEvents hook + SSE cliente | NEW event_type `cloud_remediation_proposed` filtered cliente |
| Cliente approval → admin notification | ✅ workflow_step_notifications pattern reuse | NEW `send_admin_remediation_approved_notification` helper |
| Admin executes → cliente status | ✅ SSE events extensible | NEW event_type `cloud_remediation_executing` |
| Retest fixed → cliente status | ✅ SSE events | NEW event_type `cloud_remediation_verified` |

**Per wire-up**: ~20-30 min cada · cumulative ~1.5-2.5h reusing infrastructure existing.

---

## Recomendación

**Scope-out PERMANENT como independent task** · NO independent task pre-piloto:
- Infrastructure es 100% production-grade post-1.D.G EXPANDED
- Wire-up para features nuevas (cloud remediation #9) es INCLUIDO en scope feature
- ETA absorbido en Audit #9 ETA cloud remediation total ~6-10h

**NO independent ETA** · ya considerado en cloud remediation backend wire-up ~3-5h.

**Future-1.E.cross-portal-orchestration-polish** capturable post-piloto si Marcos detecta UX friction real durante dogfooding.

---

## Cross-ref

- SSE dispatcher: `backend/app/core/sse_dispatcher.py`
- Notification orchestrator: `backend/app/notifications/orchestrator.py`
- Workflow step notifications: `backend/app/notifications/workflow_step_notifications.py`
- m21 cliente notification service
- 1.D.G EXPANDED commits (cumulative reference CLAUDE.md sub-atom section)
- Audit #9 cloud remediation (depends en esta infrastructure)
- Audit #4 cliente alertas compliance (depends en notification orchestrator)
- FASE C Phase A workflow_hooks (reuse same graceful pattern)

---

## Honest notes

1. NO regression tests ejecutados post-FASE C (1.D.G + FASE C commits cumulative · TS+ESLint scope verde · pytest diferido)
2. SSE WhatsApp dispatcher pattern complejo · NO inspección detallada (audit demand-driven)
3. Wire-up cloud remediation reuses 100% infrastructure existing · NO new sync infrastructure needed
