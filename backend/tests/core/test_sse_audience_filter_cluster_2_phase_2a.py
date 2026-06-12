"""CLUSTER 2 Phase 2A · SSE audience filter completeness tests.

Cubre:
  - CLIENTE_EVENT_TYPES whitelist contains 18 events (5 pre-existing + 12 Phase 2A
    + 1 Phase 2D `client_notification.created` DRY central wire)
  - cliente-relevant events accepted con semantic per event type
  - chat_message_new respect sender_type filter (NO own echo cliente)
  - cloud_remediation_* respect audience field si present
  - Admin-internal events still excluded (alert_new + compliance_refresh)
  - Phase 1C disconnect_requested + Phase 1E m17.plan.updated end-to-end OK
  - Phase 2D client_notification.created cliente-only namespace
"""
from __future__ import annotations


from backend.app.core.sse_dispatcher import (
    ADMIN_EVENT_TYPES,
    CLIENTE_EVENT_TYPES,
    event_matches_audience,
)


# ════════════════════════════════════════════════════════════════════
# Whitelist completeness
# ════════════════════════════════════════════════════════════════════


def test_cliente_event_types_contains_21_events():
    """CLIENTE_EVENT_TYPES cumulative 21 total.

    Phase 2A added 12 new (post 5 pre-existing m01/m02 + workflow steps).
    Phase 2D added 1 new (`client_notification.created`). Ejecutable 8 Pasada 16
    added 4 (signing.* + accompaniment). Ola 3 #14 (2026-06-04) añade
    `phase_changed` (política nueva · cliente ve su progreso de fase). FIX P2-3
    (2026-06-09) añade `document.uploaded` (gestor documental compartido realtime).
    feat/fulkro-100 (2026-06-12) añade `continuidad.draft_ready` (cliente recibe
    el borrador BIA/DRP listo para aprobar).
    """
    expected = frozenset({
        # Workflow steps (5 pre-existing including m01/m02)
        "step_completed",
        "step_unblocked",
        "step_blocked",
        "m01.categorizacion.completed",
        "m02.magerit.updated",
        # CLUSTER 2 Phase 2A NEW (12)
        "m17.plan.updated",
        "cloud.connector.disconnect_requested",
        "chat_message_new",
        "pentest_check_required",
        "cloud_remediation_proposed",
        "cloud_remediation_approved",
        "cloud_remediation_rejected",
        "cloud_remediation_executing",
        "cloud_remediation_executed",
        "cloud_remediation_failed",
        "cloud_remediation_verification_pending",
        "cloud_remediation_verified",
        "cloud_remediation_rollback_requested",
        # CLUSTER 2 Phase 2D NEW (1) · DRY central wire
        "client_notification.created",
        # Ejecutable 8 Pasada 16 (F-08-02): firma in-portal (m05_signing) + acompañamiento
        # auditoría (m_audit_accompaniment) · cliente recibe realtime (antes polling 30s).
        "signing.requested",
        "signing.signed",
        "signing.declined",
        "accompaniment.state.advanced",
        # Ola 3 #14 (2026-06-04) · phase_changed cliente-facing (transparencia)
        "phase_changed",
        # FIX P2-3 (2026-06-09) · gestor documental compartido (documento nuevo
        # en el proyecto · cliente lo ve aparecer salvo si está marcado interno)
        "document.uploaded",
        # feat/fulkro-100 (2026-06-12) · continuidad BIA/DRP draft listo
        "continuidad.draft_ready",
    })
    assert CLIENTE_EVENT_TYPES == expected, (
        f"Diff: missing={expected - CLIENTE_EVENT_TYPES} "
        f"extra={CLIENTE_EVENT_TYPES - expected}"
    )


def test_admin_internal_events_still_excluded_from_cliente_whitelist():
    """Admin-internal events NUNCA en cliente whitelist (cliente-mínimo guard).

    Ola 3 #14 (2026-06-04): phase_changed YA NO es admin-interno · pasó a
    cliente-facing (transparencia de progreso). readiness_changed/alert_new
    SIGUEN admin-internos.
    """
    admin_internal = [
        "alert_new",
        "readiness_changed",
        "compliance_dashboard_refresh_required",
        "cross_project_compliance_refresh_required",
        "auditor_clarification_new",
    ]
    for event_type in admin_internal:
        assert event_type not in CLIENTE_EVENT_TYPES or event_type in {
            "step_completed", "step_unblocked", "step_blocked",
        }, f"{event_type} should NOT leak cliente"


# ════════════════════════════════════════════════════════════════════
# Per-event audience semantic
# ════════════════════════════════════════════════════════════════════


def test_m17_plan_updated_always_cliente_accepted():
    """Phase 1E · admin PATCH task → cliente sees plan update READ-ONLY."""
    assert event_matches_audience(
        "m17.plan.updated", "cliente",
        {"task_code": "WBS-001", "status": "completed"},
    )


def test_cloud_connector_disconnect_requested_always_cliente_accepted():
    """Phase 1C · cliente own request echo (always own action)."""
    assert event_matches_audience(
        "cloud.connector.disconnect_requested", "cliente",
        {"connector_id": "abc", "provider": "microsoft_365"},
    )


def test_chat_message_new_admin_sender_accepted_cliente():
    """M21 chat · cliente recibe cuando ADMIN responde."""
    assert event_matches_audience(
        "chat_message_new", "cliente",
        {"thread_id": "xyz", "sender_type": "admin"},
    )


def test_chat_message_new_client_sender_REJECTED_cliente():
    """M21 chat · cliente NO recibe own echo cuando él escribe."""
    assert not event_matches_audience(
        "chat_message_new", "cliente",
        {"thread_id": "xyz", "sender_type": "client"},
    )


def test_pentest_check_required_always_cliente_accepted():
    """M08 ALTA · cliente recibe pentest authorization needed."""
    assert event_matches_audience(
        "pentest_check_required", "cliente",
        {"project_id": "abc"},
    )


def test_cloud_remediation_all_9_events_accepted_cliente_default():
    """Bloque 3+5 · cliente recibe full lifecycle remediation (audience absent → default cliente visible)."""
    events = [
        "cloud_remediation_proposed",
        "cloud_remediation_approved",
        "cloud_remediation_rejected",
        "cloud_remediation_executing",
        "cloud_remediation_executed",
        "cloud_remediation_failed",
        "cloud_remediation_verification_pending",
        "cloud_remediation_verified",
        "cloud_remediation_rollback_requested",
    ]
    for event_type in events:
        assert event_matches_audience(
            event_type, "cliente", {"gap_id": "abc"},
        ), f"{event_type} should be visible cliente"


def test_cloud_remediation_audience_admin_REJECTED_cliente():
    """Cloud remediation con audience=admin field → cliente NO recibe (orchestrator filter)."""
    assert not event_matches_audience(
        "cloud_remediation_proposed", "cliente",
        {"gap_id": "abc", "audience": "admin"},
    )


def test_cloud_remediation_audience_both_accepted_cliente():
    """Cloud remediation con audience=both → cliente recibe."""
    assert event_matches_audience(
        "cloud_remediation_proposed", "cliente",
        {"gap_id": "abc", "audience": "both"},
    )


# ════════════════════════════════════════════════════════════════════
# Pre-existing behavior preserved (regression guard)
# ════════════════════════════════════════════════════════════════════


def test_step_completed_admin_actor_accepted_cliente():
    """Cliente sees admin terminó step · primary_actor=admin."""
    assert event_matches_audience(
        "step_completed", "cliente",
        {"primary_actor": "admin", "template_id": "x"},
    )


def test_step_completed_cliente_actor_REJECTED():
    """Cliente NO sees own step_completed echo."""
    assert not event_matches_audience(
        "step_completed", "cliente",
        {"primary_actor": "cliente"},
    )


def test_step_unblocked_cliente_actor_accepted():
    """Cliente sees own step_unblocked when LE TOCA."""
    assert event_matches_audience(
        "step_unblocked", "cliente",
        {"primary_actor": "cliente"},
    )


def test_m01_categorizacion_completed_admin_actor_accepted_cliente():
    """Phase 1A · cliente sync admin finalize categorización."""
    assert event_matches_audience(
        "m01.categorizacion.completed", "cliente",
        {"primary_actor": "admin", "system_id": "x"},
    )


def test_m02_magerit_updated_admin_actor_accepted_cliente():
    """Phase 1B · cliente sync admin congeló MAGERIT analysis."""
    assert event_matches_audience(
        "m02.magerit.updated", "cliente",
        {"primary_actor": "admin", "analysis_id": "x"},
    )


def test_alert_new_REJECTED_cliente():
    """Admin-internal alert_new NUNCA leak cliente."""
    assert not event_matches_audience(
        "alert_new", "cliente",
        {"alert_id": "x"},
    )


def test_admin_receives_all_admin_event_types():
    """Admin recibe TODOS los ADMIN_EVENT_TYPES.

    chat_message_new (CLUSTER 5 Phase 5C) needs sender_type filter · data
    default ``sender_type="client"`` matches the admin recv path.
    """
    for event_type in ADMIN_EVENT_TYPES:
        assert event_matches_audience(
            event_type, "admin",
            {"primary_actor": "anything", "sender_type": "client"},
        ), f"admin should receive {event_type}"


# ════════════════════════════════════════════════════════════════════
# CLUSTER 5 Phase 5C · chat realtime admin recv cross-actor filter
# ════════════════════════════════════════════════════════════════════


def test_chat_message_new_in_admin_event_types_cluster_5_phase_5c():
    """Phase 5C delta · chat_message_new added to ADMIN_EVENT_TYPES whitelist."""
    assert "chat_message_new" in ADMIN_EVENT_TYPES


def test_chat_message_new_client_sender_accepted_admin():
    """Admin recibe chat_message_new cuando sender_type=client (cliente escribió)."""
    assert event_matches_audience(
        "chat_message_new", "admin",
        {"thread_id": "abc", "sender_type": "client"},
    )


def test_chat_message_new_admin_sender_REJECTED_admin():
    """Admin NO recibe own echo cuando sender_type=admin (own reply)."""
    assert not event_matches_audience(
        "chat_message_new", "admin",
        {"thread_id": "abc", "sender_type": "admin"},
    )


def test_unknown_audience_returns_false():
    """audience desconocido NO matches (defensive)."""
    assert not event_matches_audience(
        "step_completed", "auditor", {"primary_actor": "admin"},
    )
    assert not event_matches_audience(
        "step_completed", "", {"primary_actor": "admin"},
    )
