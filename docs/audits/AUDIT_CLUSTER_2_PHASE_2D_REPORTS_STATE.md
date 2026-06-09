# AUDIT CLUSTER 2 Phase 2D · M21 Reports Cliente Auto-Refetch SSE Empirical State

**Sesión**: 3B-2B.8 CLUSTER 2 Path B Phase 2D
**Fecha**: 2026-05-26
**Ejecutor**: Phase 2D.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined wire-completeness gap-fix · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 2D asumió necesidad de cliente "reports page" subscribe SSE auto-refetch (events `m21.report.generated` / `m21.report.updated`). Empirical reality:

- ❌ **NO existe dedicated `/client-portal/reports` page** (no encontrado en navigation cliente)
- ✅ **Reports cliente surface via `/client-portal/inbox`** (NotificationsInboxPanel · ClientNotification type=`report_available` already supported · `TYPE_META` row 49)
- ✅ **`emit_client_notification` central function existe** (m21_portal_cliente/notification_service.py · 17 VALID_TYPES incl `report_available`)
- ✅ **`useInbox` polls every 30s + `useUnreadCount` polls every 15s** (functional baseline)
- ✅ **SSE infrastructure existing + CLIENTE_EVENT_TYPES whitelist** (Phase 2A wire-completeness expanded 12+ events)
- ✅ **`useClientProjectEvents` hook + `invalidateQueries` propagation pattern** functional empirical
- ❌ **NO SSE emit currently on ClientNotification creation** (only 30s/15s polling refresh inbox)
- ❌ **Only 1 motor emit `report_available` empirical** (`m_cloud_connectors/digest_service.py:246` monthly cloud digest)

**Gap identified**: emit_client_notification central function NO emit SSE event post-persist · cliente inbox depends 30s polling lag. Architectural pattern wire-completeness fix vs greenfield reports page assumption.

**Filosofía cliente-mínimo guard**: SSE invalidation on notification creation 100% aligned · cliente RECIBE realtime · NO opera nada.

ETA refined: ~1-1.5h vs briefing 1.5-2h nominal (-25% OPS-045 54ª manifestation · DRY reuse central function · NO greenfield reports page).

---

## Phase 2D.0.1 · Empirical surface cliente reports map

### Cliente portal pages relacionadas reports

| Page | Path | Function |
|------|------|----------|
| **inbox** | `/client-portal/inbox` | NotificationsInboxPanel · ALL ClientNotification types incl `report_available` + 16 más (acta_review · evidence_request · etc.) |
| dpc-anual | `/client-portal/dpc-anual` | DPC anual (NOT report · annual signing flow) |
| conformidad | `/client-portal/conformidad` | Conformity declaration (NOT report · pre-audit signing) |
| categorizacion | `/client-portal/categorizacion` | M01 categorización view (Phase 1A target_url) |
| magerit | `/client-portal/magerit` | M02 MAGERIT view (Phase 1B target_url) |
| plan | `/client-portal/plan` | M17 plan Gantt (Phase 1E target_url) |
| remediaciones | `/client-portal/remediaciones` | Cloud remediation lifecycle |

**Conclusion**: NO dedicated `/client-portal/reports` page exists · inbox surface ALL notifications cliente including reports.

### ClientNotification VALID_TYPES (17 cumulative)

`backend/app/motors/m21_portal_cliente/notification_service.py`:
- evidence_request · acta_review · retainer_offer · retainer_reconsideration
- onboarding_ready · generic_alert · invoice_review · risk_validation
- compliance_confirmation · meeting_invite · scope_change_validation · incident_report
- nps_survey · vote_request · **report_available** · renewal_campaign · info_request

### Emitters existing `report_available` empirical

| Motor | File:line | Event scope |
|-------|-----------|-------------|
| m_cloud_connectors | digest_service.py:246 | Monthly compliance digest snapshot |
| **TBD post-piloto** | retainer reports + compliance monitor reports + audit draft reports | Future-X emit `report_available` cuando wire-in demanded (DRY reuse central fn) |

---

## Phase 2D.0.2 · SSE infrastructure existing + emit pattern audit

### CLIENTE_EVENT_TYPES whitelist (post Phase 2A · 22 events)

`backend/app/core/sse_dispatcher.py:111-136`:
- step_completed · step_unblocked · step_blocked
- m01.categorizacion.completed · m02.magerit.updated · m17.plan.updated
- cloud.connector.disconnect_requested + 4 lifecycle
- chat_message_new · pentest_check_required
- cloud_remediation_* (9 events)

**Gap**: `client_notification.created` NOT en whitelist · ClientNotification emit NO triggers SSE realtime.

### emit_client_notification central function

`backend/app/motors/m21_portal_cliente/notification_service.py`:
- **API**: `emit_client_notification(db, project_id, client_user_id, type, title, body, target_url, priority, payload, emitted_by_motor)`
- **Storage**: ClientNotification model persist (SAN-E v3.MB-4.bis3 in-app inbox only)
- **NO SSE dispatch currently** (poll-based refresh inbox UI)
- **DRY opportunity**: ADD `sse_dispatcher.publish` post-persist best-effort · 1 central wire-point cubre ALL future emitters

### useInbox hook current

`frontend/hooks/useClientNotifications.ts`:
- `useInbox`: polling 30s · staleTime 30s
- `useUnreadCount`: polling 15s · staleTime 15s
- `useMarkRead` / `useDismiss` / `useMarkActioned`: mutation + invalidate `["client-inbox"]`

**Gap**: NO SSE subscribe layer · refresh 30s lag worst-case empirical.

### useClientProjectEvents pattern reuse

`frontend/hooks/useClientProjectEvents.ts`:
- Subscribe SSE `/api/v1/client-portal/projects/{id}/events`
- Audience-filtered cliente (event_matches_audience cliente filter sse_dispatcher.py:139-207)
- Handler pattern: per-event callback + `invalidateQueries` propagation

---

## Phase 2D.0.3 · audit_log emit current state

### Cliente "viewed report" audit_log

Search `cliente.report.viewed` accion empirical: **NO ENCONTRADO** empirical en codebase actual.

Existing similar patterns:
- `cliente.categorizacion.viewed` (Phase 1A m21)
- `cliente.magerit.viewed` (Phase 1B m02 portal_api)
- `cliente.plan.viewed` (Phase 1E m17 portal_api)
- `cliente.cloud_connector.viewed` (Phase 1C api_cliente)

**Gap**: NO audit_log emit cuando cliente views report (inbox notif click).

---

## Phase 2D.0.4 · Recommended Phase 2D refined scope (~1-1.5h)

### Phase 2D.1 implementation (~45-60 min)

**Step 1 · sse_dispatcher.py**: ADD `client_notification.created` to CLIENTE_EVENT_TYPES whitelist (~10 min)
- Audience filter cliente: respect `client_user_id` ownership (data field) · audit_log Sub-atom 5.A 3-way OR
- Forward-compat all ClientNotification types

**Step 2 · notification_service.emit_client_notification**: ADD SSE dispatch post-persist (~15 min)
- Best-effort try/except (notify_best_effort pattern existing Bloque 3+5)
- Channel: `project:{project_id}` (existing cliente SSE channel)
- Event type: `client_notification.created`
- Data: `{notification_id, type, title, target_url, priority, client_user_id, emitted_by_motor, _timestamp}`
- audit_log emit `cliente.notification.dispatched` (Sub-atom 5.A 3-way OR project_id + client_id)

**Step 3 · useClientProjectEvents**: ADD `client_notification.created` event handler (~10 min)
- Extend `ClientSseEventType` union
- Add event listener + handler invalidateQueries `["client-inbox"]`
- Forward-compat `onClientNotificationCreated` optional callback

**Step 4 · NotificationsInboxPanel + useInbox**: Wire SSE auto-invalidate (~10 min)
- Subscribe via useClientProjectEvents (project_id from active project store)
- Reduce polling to 60s fallback (was 30s · SSE primary)
- Forward-compat empirical: SSE fails → polling resumes
- audit_log emit `cliente.notification.opened` on target_url click (Sub-atom 5.A 3-way OR)

### Phase 2D.2 tests (~30-45 min)

**Backend tests (3-4 tests)**:
- Test emit_client_notification SSE dispatch fired post-persist
- Test emit_client_notification SSE dispatch graceful degradation (dispatcher fail · primary persist NOT blocked)
- Test audit_log entry `cliente.notification.dispatched` con project_id + client_id propagated (Sub-atom 5.A)
- Test SSE event_matches_audience cliente filter for `client_notification.created` respect ownership

**Frontend tests** (deferred polish):
- Optional E2E Playwright spec verify SSE auto-refetch (Future-1.E.client-notification-sse-e2e ~30 min)

---

## ETA refined Phase 2D

- **Briefing nominal**: ~1.5-2h
- **Empirical refined**: ~1-1.5h (wire-completeness gap-fix · NO greenfield · DRY reuse central function)
- **OPS-045 54ª manifestation**: -25% to -50% vs nominal (audit-first reveals infrastructure complete · just wire SSE on existing fn)

---

## Filosofía cliente-mínimo compliance

SSE invalidation on notification creation evaluated:
- Cliente RECIBE realtime notification appearance · NO opera nada · ✅ aligned
- Cliente abre inbox · click "Ir" → target_url · NO crea contenido · ✅ aligned
- audit_log `cliente.notification.opened` traces visualization · ✅ aligned

**ZERO admin-internal operations leaked cliente**. Notification metadata is cliente-facing only.

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing scope intent (cliente realtime report auto-refetch) ratified · refined a wire-completeness gap-fix scope concrete (central function SSE dispatch wire · NOT greenfield reports page assumption).

Briefing assumption "M21 reports page" replaced empirical "inbox surface ALL notifications cliente incl reports" · scope alignment achieved without losing intent.

---

## Patterns potencialmente formalizables Phase 2D

- **Central notification fn + SSE dispatch DRY pattern** (emit_client_notification wraps persist + SSE in 1 fn · forward-compat ALL emitters automatic SSE-enabled)
- **Hybrid SSE primary + polling fallback** (useInbox + useClientProjectEvents · graceful degradation EventSource fails)
- **audit_log `cliente.notification.dispatched` emit post-SSE** (trace dispatch lifecycle · forward-compat reports/auditor analysis)

---

## Decisión pendiente

⏸️ **Architect approve Phase 2D.1 refined scope**:
- ADD `client_notification.created` to CLIENTE_EVENT_TYPES whitelist + audience filter
- ADD SSE dispatch + audit_log in `emit_client_notification` (best-effort try/except)
- EXTEND `useClientProjectEvents` + `NotificationsInboxPanel` SSE subscribe + invalidateQueries
- 3-4 backend tests + audit_log Sub-atom 5.A coverage
- ETA refined ~1-1.5h
