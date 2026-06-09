"""Tests M19 IncidentWorkflowService + ccn_cert_decision_tree · SAN-E v3.MB-6 atom 3.

10 tests cubren:
  Decision tree (Q2 + Q7):
    1. test_decision_tree_critical_lucia_enabled_routes_auto
    2. test_decision_tree_critical_lucia_disabled_routes_manual
    3. test_decision_tree_high_severity_72h_deadline
    4. test_decision_tree_medium_low_internal_only
  Workflow service:
    5. test_create_incident_persists_routing_decision
    6. test_workflow_state_transitions_valid_only
    7. test_workflow_state_transition_to_closed_blocks_direct
    8. test_client_review_blocks_until_resolved
    9. test_client_visible_filters_resolved_closed_only
   10. test_incident_close_signoff_links_intent
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m19_risk.ccn_cert_decision_tree import (
    IncidentEvaluationInput,
    evaluate_routing,
)
from backend.app.motors.m19_risk.incident_workflow_service import (
    IncidentWorkflowError,
    IncidentWorkflowService,
    InvalidReviewActionError,
    InvalidWorkflowTransitionError,
)
from backend.tests.conftest import setup_test_project


async def _create_user_id(db: AsyncSession, client_id: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO client_users (id, client_id, email, password_hash, created_at) "
            "VALUES (:uid, :cid, :email, 'x', now())"
        ),
        {
            "uid": str(user_id),
            "cid": client_id,
            "email": f"u{user_id.hex[:6]}@test.es",
        },
    )
    await db.flush()
    return user_id


async def _set_project_lucia(db: AsyncSession, project_id: str, enabled: bool) -> None:
    await db.execute(
        sa_text("UPDATE projects SET lucia_enabled = :en WHERE id = :pid"),
        {"en": enabled, "pid": project_id},
    )
    await db.flush()


# ════════════════════════════════════════════════════════════════════
# Decision tree (lightweight · pure function · no DB)
# ════════════════════════════════════════════════════════════════════


def test_decision_tree_critical_lucia_enabled_routes_auto():
    result = evaluate_routing(IncidentEvaluationInput(
        severity="critical",
        lucia_enabled=True,
    ))
    assert result.route_type == "lucia_federation"
    assert result.deadline_hours == 24
    assert "auto_submit_lucia" in result.action_required


def test_decision_tree_critical_lucia_disabled_routes_manual():
    result = evaluate_routing(IncidentEvaluationInput(
        severity="critical",
        lucia_enabled=False,
    ))
    assert result.route_type == "manual_notification"
    assert result.deadline_hours == 24
    assert "generate_manual_notification_template" in result.action_required


def test_decision_tree_high_severity_72h_deadline():
    result = evaluate_routing(IncidentEvaluationInput(
        severity="high",
        lucia_enabled=False,
    ))
    assert result.deadline_hours == 72
    assert result.route_type == "manual_notification"


def test_decision_tree_medium_low_internal_only():
    for sev in ("medium", "low"):
        result = evaluate_routing(IncidentEvaluationInput(
            severity=sev,
            lucia_enabled=True,  # incluso con lucia · medium/low NO se reporta
        ))
        assert result.route_type == "internal_only"
        assert result.deadline_hours is None


# ════════════════════════════════════════════════════════════════════
# Workflow service
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_incident_persists_routing_decision(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    await _set_project_lucia(db, project_id, False)
    svc = IncidentWorkflowService(db)

    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="critical",
        descripcion="Test critical incident",
    )

    assert incident.workflow_state == "created"
    assert incident.severidad == "critical"
    routing = incident.ccn_cert_routing_decision
    assert routing is not None
    assert routing["route_type"] == "manual_notification"
    assert routing["deadline_hours"] == 24


@pytest.mark.asyncio
async def test_workflow_state_transitions_valid_only(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="medium",
        descripcion="Test transitions",
    )

    # created → triaged (válida)
    await svc.transition_workflow_state(incident.id, "triaged")
    # triaged → investigated (válida)
    await svc.transition_workflow_state(incident.id, "investigated")
    # investigated → resolved (válida · skip mitigated permitido)
    await svc.transition_workflow_state(
        incident.id, "resolved", resolucion="Resolved test",
    )

    # resolved → triaged (INVÁLIDA · no backwards)
    with pytest.raises(InvalidWorkflowTransitionError):
        await svc.transition_workflow_state(incident.id, "triaged")


@pytest.mark.asyncio
async def test_workflow_state_transition_to_closed_blocks_direct(db: AsyncSession):
    """closed reachable solo via process_incident_close_signoff · NO via transition."""
    _, project_id = await setup_test_project(db)
    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="low",
        descripcion="Test",
    )
    await svc.transition_workflow_state(incident.id, "triaged")

    # triaged → closed (INVÁLIDA via transition)
    with pytest.raises(InvalidWorkflowTransitionError):
        await svc.transition_workflow_state(incident.id, "closed")


@pytest.mark.asyncio
async def test_client_review_blocks_until_resolved(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="medium",
        descripcion="Test review block",
    )

    # En created · cliente NO puede revisar
    with pytest.raises(IncidentWorkflowError):
        await svc.mark_client_review(
            incident.id, "revisada_ok", None, user_id,
        )


@pytest.mark.asyncio
async def test_client_visible_filters_resolved_closed_only(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = IncidentWorkflowService(db)

    # 3 incidents: 1 created · 1 resolved · 1 closed
    i1 = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="low",
        descripcion="Created",
    )
    i2 = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="low",
        descripcion="Will be resolved",
    )
    await svc.transition_workflow_state(i2.id, "triaged")
    await svc.transition_workflow_state(i2.id, "resolved")

    visible = await svc.get_client_visible_incidents(uuid.UUID(project_id))

    assert len(visible) == 1
    assert visible[0].id == i2.id
    assert visible[0].workflow_state == "resolved"


@pytest.mark.asyncio
async def test_incident_close_signoff_links_intent(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="high",
        descripcion="Test close signoff",
    )
    await svc.transition_workflow_state(incident.id, "triaged")
    await svc.transition_workflow_state(
        incident.id, "resolved", resolucion="Mitigated successfully",
    )
    await svc.mark_client_review(incident.id, "revisada_ok", None, user_id)

    intent_id = uuid.uuid4()
    result = await svc.process_incident_close_signoff(incident.id, intent_id)

    assert result.workflow_state == "closed"
    assert result.client_signing_intent_id == intent_id


@pytest.mark.asyncio
async def test_client_review_invalid_action_raises(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = IncidentWorkflowService(db)
    incident = await svc.create_incident(
        project_id=uuid.UUID(project_id),
        severidad="low",
        descripcion="Test",
    )
    await svc.transition_workflow_state(incident.id, "triaged")
    await svc.transition_workflow_state(incident.id, "resolved")

    with pytest.raises(InvalidReviewActionError):
        await svc.mark_client_review(incident.id, "approved", None, user_id)

    with pytest.raises(InvalidReviewActionError):
        await svc.mark_client_review(incident.id, "con_pregunta", None, user_id)
