# AUDIT CLUSTER 2 Phase 2C · Coach Proactivo Cliente Nudges/Reminders State

**Sesión**: 3B-2B.8 CLUSTER 2 Path B Phase 2C
**Fecha**: 2026-05-26
**Ejecutor**: Phase 2C.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · ALL infrastructure exists · pure additive scope · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 2C asumió necesidad de NEW nudge scheduler infrastructure. Empirical reality: ALL infrastructure pre-existing · scope refined a pure additive composition reusing 3 services existing.

- ✅ **Celery beat scheduler EXISTS** ([celery_app.py](../../backend/app/core/celery_app.py)) con 20+ scheduled tasks (daily/weekly/monthly/quarterly) · `notifications.scan_client_inactivity` daily 09:00 ES pattern reference
- ✅ **compute_workflow_state Phase 1D EXISTS** ([workflow_state_scanner.py](../../backend/app/motors/m11_copiloto/workflow_state_scanner.py)) · pure functional · `WorkflowScannerOptions(role_filter='cliente')` returns `next_cliente_actions` con priority + target_url · **PERFECT for nudge derivation**
- ✅ **NotificationOrchestrator + emit_client_notification EXIST** (Phase 2B verified · 12 motor adapters · 17 VALID_TYPES · 3 channels email + portal_sse + whatsapp)
- ✅ **CopilotoDock proactive hint banner EXISTS** (Phase 1D) · displays urgent/normal/low priority visual
- ✅ **audit_log Sub-atom 5.A pattern EXISTS** (cumulative cross-cluster)
- ✅ **AlertService.trigger_alert pattern EXISTS** ([m18_communication/alert_service.py](../../backend/app/motors/m18_communication/alert_service.py)) reference for client_inactivity scan

**Scope refined**: pure additive composition NEW `nudge_scheduler.py` service + NEW Celery beat entry + NEW audit_log accion + NO new schemas/migrations/UI.

ETA refined ~1.5h vs briefing 2-3h nominal (OPS-045 54ª manifestation -25% to -50% · audit reveals infrastructure complete).

---

## Phase 2C.0.1 · Celery beat scheduler empirical

**Path**: [backend/app/core/celery_app.py](../../backend/app/core/celery_app.py)

20+ scheduled tasks existing organized per motor:
- M07 evidence freshness daily 06:00
- M23 retainer overdue daily 08:00 + renewal daily 07:00 + monthly invoices day 1
- M25 lifecycle grace period daily 04:30 + backup expiration daily 05:00
- M26 backup full weekly Sunday 02:00 + incremental daily 03:00 + verify weekly + restore monthly
- M27 conformity biannual + DPC anual daily 08:00/08:30
- **`notifications.scan_client_inactivity` daily 09:00 ES** ← reference pattern for Phase 2C
- m_compliance_monitor daily/weekly/monthly/quarterly
- m_cloud_connectors daily diagnosis 04:00 + monthly digest day 1 09:00

**Pattern reference**: `notifications.scan_client_inactivity` (Sesión SAN-D MB-16.4 · ADR-039). Daily scan per ClientUser → AlertService.trigger_alert + NotificationOrchestrator.enqueue_with_template `client_inactivity_admin`.

## Phase 2C.0.2 · compute_workflow_state Phase 1D reusability

**Path**: [backend/app/motors/m11_copiloto/workflow_state_scanner.py](../../backend/app/motors/m11_copiloto/workflow_state_scanner.py)

Pure functional service ALTAMENTE reusable (Pattern #7 cumulative · mirror Phase C3):
- `WorkflowScannerOptions(role_filter='cliente')` returns ONLY cliente actions
- `next_cliente_actions: list[ActionHint]` per WorkflowPhase (10 fases)
- ActionHint: `motor + action + description_cliente + priority + target_url`
- Priority urgent/normal/low (weight sorting)
- Blockers detected: DdA pendiente firma · pentest ALTA auth · auditor externo CONFORMIDAD

**Empirical verified**: Phase 1D 12/12 tests PASS + Phase 1A-1E cumulative cross-suite 920+/920+. Service reusable Sesión 3B-2B.9 admin + Sesión 3B-2B.10 simulacro (architect-validated).

## Phase 2C.0.3 · Notification infrastructure empirical

**emit_client_notification** ([m21_portal_cliente/notification_service.py](../../backend/app/motors/m21_portal_cliente/notification_service.py)):
- 17 VALID_TYPES including `generic_alert` (Phase 2C nudges) + `info_request` + others
- 4 VALID_PRIORITIES (low/normal/high/urgent)
- In-app inbox (ClientNotification model)

**NotificationOrchestrator** ([orchestrator.py](../../backend/app/notifications/orchestrator.py)):
- Multi-channel (email + portal_sse + whatsapp)
- DND-aware
- Template resolver YAML
- 12 motor adapters existing (notify_chat_admin_reply · notify_task_assigned · etc.)

**Decision Phase 2C**: use `emit_client_notification` (simpler interface · in-app inbox) for nudges · email reminders DEFER Future-X cuando volumen empirical justifica template overhead OR use `enqueue_with_template` directo si template exists.

## Phase 2C.0.4 · Coach proactive concept gap analysis

**Hint pasivo (Phase 1D current state)**:
- Cliente abre CopilotoDock → fetch GET /hint → display banner
- Pull-driven · NO push si cliente NO abre dock
- Sin cooldown · NO scheduled
- Sin email reminder

**Coach proactivo (Phase 2C target)**:
- Push-driven · daily scan cross all active projects
- Per project: compute_workflow_state cliente → top action urgent/normal
- Cooldown check: si nudge mismo `(project_id, action)` <24h → skip (avoid spam)
- Emit ClientNotification (in-app inbox) + audit_log emit `coach.nudge.dispatched`
- Email reminder DEFER Future-X (in-app first · email when cliente explicitly opts in)

**Filosofía cliente-mínimo guards**:
- Nudges son ClientNotification VE/RECIBE pattern (NO operations · NO ENS authoring)
- R29 friendly tone preserved (descriptions Phase 1D already R29 compliant)
- Cooldown 24h prevents spam · cliente NO presión psicológica
- "Sin prisa" embedded en descriptions cliente Phase 1D actions

## Phase 2C.0.5 · NEW service design recommended

### `backend/app/motors/m11_copiloto/nudge_scheduler.py`

```python
@dataclass
class NudgeAction:
    project_id: str
    client_user_id: str
    action: str  # e.g. 'sign_dda'
    motor: str   # e.g. 'm03'
    title: str   # R29 friendly Spanish
    body: str    # R29 friendly Spanish
    target_url: str
    priority: str  # urgent | normal
    notification_type: str  # generic_alert | info_request

async def compute_pending_nudges(
    db: AsyncSession, *, cooldown_hours: int = 24,
) -> list[NudgeAction]:
    """Pure functional · scan active projects · derive nudges con cooldown check.

    1. Query active projects (lifecycle_state in SIGNED/ACTIVE/CERTIFIED/RETAINER)
    2. Per project: compute_workflow_state(role_filter='cliente') → top action
    3. Filter top action priority IN ('urgent', 'normal') · skip low
    4. Cooldown check: query last cliente.notification of payload.source ==
       f'coach_nudge:{action}' for (project_id, client_user_id) · skip si <cooldown_hours
    5. Return list[NudgeAction] · ordered priority urgent first
    """

async def dispatch_nudges(db, nudges: list[NudgeAction]) -> dict:
    """Best-effort emit ClientNotification + audit_log per nudge.
    Pattern #14 sustained (independent dispatch · graceful single failure)."""
```

### Celery beat entry (additive)

```python
celery_app.conf.beat_schedule['coach-scan-pending-nudges'] = {
    "task": "coach.scan_pending_nudges",
    "schedule": crontab(hour=9, minute=15),  # 15 min after client_inactivity scan
}
```

### Backend tests recommended (4-6)

- test_compute_pending_nudges_returns_urgent_actions
- test_cooldown_24h_blocks_duplicate_nudge
- test_cliente_id_rls_isolation_cross_project (Sub-atom 5.A)
- test_dispatch_nudges_emits_client_notification_with_audit_log
- test_no_nudges_returned_when_workflow_state_no_cliente_actions
- test_filosofía_cliente_mínimo_descriptions_R29_friendly (no presión patterns)

## ETA refined Phase 2C

- **Briefing nominal**: ~2-3h
- **Empirical refined**: ~1.5h (composition existing services + Celery beat entry · NO new schemas/migrations/UI)
- **OPS-045 54ª manifestation**: -25% to -50% vs nominal (audit reveals infrastructure complete · 3 services reusable)

## Phase 2C.1 deliverables refined

1. NEW `nudge_scheduler.py` service (pure functional · compute_pending_nudges + dispatch_nudges)
2. Celery task `coach.scan_pending_nudges` daily 09:15 ES
3. Add audit_log accion `coach.nudge.dispatched` (Sub-atom 5.A 3-way OR)
4. Backend tests 4-6 (compute + cooldown + RLS + dispatch + cliente-mínimo R29)
5. **NO frontend changes** (CopilotoDock Phase 1D already displays hints · nudges land en inbox existing)
6. **NO new migrations** (reuse ClientNotification + audit_log tables)
7. **NO email/whatsapp** Phase 2C scope (DEFER Future-X cuando empirical demand)

## Filosofía cliente-mínimo compliance

| Aspect | Aligned? |
|--------|----------|
| Nudge content (R29 friendly descriptions Phase 1D) | ✅ "Sin prisa · cuando puedas" embedded |
| Cooldown 24h (NO spam · NO presión psicológica) | ✅ aligned |
| Cliente acción required (cliente makes own decision) | ✅ aligned (target_url goes to cliente own page) |
| NO admin operations leaked | ✅ aligned (role_filter='cliente' enforced) |
| NO ENS authoring forced cliente | ✅ aligned (nudges link to cliente VE/SIGN/REVIEW pages) |

**ZERO violations cliente-mínimo filosofía** · 100% compliant.

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (coach proactivo nudges) ratified · scope refined a pure additive composition (1 service file + 1 Celery beat entry + tests) vs greenfield assumption.

## Patterns formalizable Phase 2C

15. **Proactive nudge scheduler pure functional pattern** (mirror Phase C3 · pure functional service compute_pending_nudges · cooldown-aware via audit_log/ClientNotification history query · reusable cross-consumer · cliente-mínimo R29 friendly tone preserved)

## Decisión pendiente

⏸️ **Architect approve Phase 2C.1 refined scope**:
- NEW nudge_scheduler.py service (pure functional)
- Celery beat coach-scan-pending-nudges daily 09:15 ES
- audit_log emit coach.nudge.dispatched (Sub-atom 5.A)
- NO frontend changes (Phase 1D CopilotoDock + inbox infrastructure suffices)
- NO email Phase 2C (DEFER Future-X email reminder cuando demand)
- ETA refined ~1.5h
