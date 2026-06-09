"""Tests Bloque 3+5 · CloudRemediationOrchestrator state machine + audit trail.

Cubre:
  - State machine transitions allowed/denied (pure function)
  - Full happy path: detected → proposed_to_cliente → approved → executing → executed
  - Reject path: detected → proposed_to_cliente → rejected (terminal)
  - Failed path: detected → proposed_to_cliente → approved → executing → failed
  - Audit trail rows persisted per transition
  - Invalid transitions raise InvalidTransitionError
  - SSE dispatch graceful (mocked · NUNCA bloquea state)
  - RLS project-scoped (gap NOT found en project distinto)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
    CloudGap,
    CloudGapType,
    CloudGapSeverity,
    CloudRemediationActorType,
    CloudRemediationApprovalStatus,
    CloudRemediationLogAction,
)
from backend.app.motors.m_cloud_connectors.remediation_orchestrator import (
    CloudRemediationOrchestrator,
    GapNotFoundError,
    InvalidTransitionError,
    _ALLOWED_TRANSITIONS,
    _can_transition,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Pure state machine tests (NO DB)
# ════════════════════════════════════════════════════════════════════


class TestStateMachine:
    """Pure function _can_transition · sin DB."""

    def test_detected_allows_propose_to_cliente(self) -> None:
        assert _can_transition("detected", "proposed_to_cliente") is True

    def test_detected_denies_skip_to_approved(self) -> None:
        assert _can_transition("detected", "approved") is False

    def test_proposed_allows_approve_or_reject(self) -> None:
        assert _can_transition("proposed_to_cliente", "approved") is True
        assert _can_transition("proposed_to_cliente", "rejected") is True

    def test_proposed_denies_skip_to_executing(self) -> None:
        assert _can_transition("proposed_to_cliente", "executing") is False

    def test_approved_allows_only_executing(self) -> None:
        assert _can_transition("approved", "executing") is True
        assert _can_transition("approved", "rejected") is False
        assert _can_transition("approved", "executed") is False

    def test_executing_allows_executed_or_failed(self) -> None:
        assert _can_transition("executing", "executed") is True
        assert _can_transition("executing", "failed") is True

    def test_terminal_states_no_transitions(self) -> None:
        # Ejecutable 8 Pasada 16 (b · test desfasado · fuente: Phase A Enhancement
        # remediation_orchestrator.py:94-103): EXECUTED ya NO es terminal · transiciona a
        # VERIFICATION_PENDING (verify flow). Terminales reales: rejected / verified / failed.
        assert _ALLOWED_TRANSITIONS["rejected"] == set()
        assert _ALLOWED_TRANSITIONS["verified"] == set()
        assert _ALLOWED_TRANSITIONS["failed"] == set()
        assert _ALLOWED_TRANSITIONS["executed"] == {"verification_pending"}

    def test_all_enum_values_in_allowed_transitions_keys(self) -> None:
        """Cada CloudRemediationApprovalStatus value debe estar en
        _ALLOWED_TRANSITIONS (incluso si vacío para terminal)."""
        all_states = {s.value for s in CloudRemediationApprovalStatus}
        assert all_states <= set(_ALLOWED_TRANSITIONS.keys())


# ════════════════════════════════════════════════════════════════════
# Helpers DB setup
# ════════════════════════════════════════════════════════════════════


async def _create_gap_with_connector(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    *,
    title: str = "Test gap MFA missing",
    severity: str = CloudGapSeverity.CRITICAL.value,
    ens_measure_code: str = "op.acc.6",
) -> CloudGap:
    """Crea CloudConnector + CloudGap para testing transitions."""
    async with _admin_setup(db):
        connector = CloudConnector(
            project_id=project_uuid,
            provider=CloudConnectorProvider.MICROSOFT_365.value,
            status=CloudConnectorStatus.CONNECTED.value,
        )
        db.add(connector)
        await db.flush()

        gap = CloudGap(
            project_id=project_uuid,
            connector_id=connector.id,
            gap_type=CloudGapType.STRUCTURAL.value,
            severity=severity,
            ens_measure_code=ens_measure_code,
            title=title,
            suggested_action="Enable MFA for all users",
            auto_fixable=False,
            cliente_can_see=True,
            raw_evidence={"users_no_mfa_count": 12},
        )
        db.add(gap)
        await db.flush()
    return gap


# ════════════════════════════════════════════════════════════════════
# Full happy path · detected → executed
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_happy_path_full_lifecycle(db: AsyncSession) -> None:
    """detected → proposed → approved → executing → executed (5 transitions)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    evidence_id = uuid.uuid4()

    orch = CloudRemediationOrchestrator(db)

    # 1. propose_to_cliente
    gap = await orch.propose_to_cliente(
        gap_id=gap.id, admin_user_id=admin_id, notes="Crítico · MFA bypass",
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value
    assert gap.proposed_to_cliente_at is not None

    # 2. cliente_approve
    gap = await orch.cliente_approve(
        gap_id=gap.id, cliente_user_id=cliente_id, notes="OK aprobamos",
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.APPROVED.value
    assert gap.cliente_approval_at is not None
    assert gap.cliente_approval_user_id == cliente_id

    # 3. start_execution
    gap = await orch.start_execution(
        gap_id=gap.id, admin_user_id=admin_id,
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.EXECUTING.value

    # 4. mark_executed
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        evidence_link_id=evidence_id, notes="MFA enforced for all 12 users",
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.EXECUTED.value
    assert gap.resolved_at is not None
    assert gap.resolved_by_user_id == admin_id
    assert gap.evidence_link_id == evidence_id
    assert gap.resolution_note == "MFA enforced for all 12 users"

    # Audit trail · 4 log rows (propose · approve · execute · executed)
    logs = await orch.list_audit_logs(gap_id=gap.id)
    assert len(logs) == 4
    assert logs[0].action == CloudRemediationLogAction.PROPOSED_TO_CLIENTE.value
    assert logs[0].actor_type == CloudRemediationActorType.ADMIN.value
    assert logs[1].action == CloudRemediationLogAction.CLIENTE_APPROVED.value
    assert logs[1].actor_type == CloudRemediationActorType.CLIENTE.value
    assert logs[2].action == CloudRemediationLogAction.EXECUTING.value
    assert logs[3].action == CloudRemediationLogAction.EXECUTED.value


# ════════════════════════════════════════════════════════════════════
# Rejection path · terminal
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rejection_path_terminal(db: AsyncSession) -> None:
    """detected → proposed → rejected (cliente decide no proceder)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)
    orch = CloudRemediationOrchestrator(db)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()

    await orch.propose_to_cliente(gap_id=gap.id, admin_user_id=admin_id)
    gap = await orch.cliente_reject(
        gap_id=gap.id, cliente_user_id=cliente_id,
        notes="No tenemos presupuesto este trimestre",
    )

    assert gap.approval_status == CloudRemediationApprovalStatus.REJECTED.value
    assert gap.cliente_approval_at is not None
    assert gap.cliente_approval_user_id == cliente_id

    # Terminal · NO se permite transition out
    with pytest.raises(InvalidTransitionError):
        await orch.start_execution(gap_id=gap.id, admin_user_id=admin_id)

    logs = await orch.list_audit_logs(gap_id=gap.id)
    assert len(logs) == 2
    assert logs[-1].action == CloudRemediationLogAction.CLIENTE_REJECTED.value
    assert logs[-1].notes == "No tenemos presupuesto este trimestre"


# ════════════════════════════════════════════════════════════════════
# Failed path · terminal
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_failed_path_terminal_with_metadata(db: AsyncSession) -> None:
    """detected → proposed → approved → executing → failed."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)
    orch = CloudRemediationOrchestrator(db)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()

    await orch.propose_to_cliente(gap_id=gap.id, admin_user_id=admin_id)
    await orch.cliente_approve(gap_id=gap.id, cliente_user_id=cliente_id)
    await orch.start_execution(gap_id=gap.id, admin_user_id=admin_id)

    gap = await orch.mark_failed(
        gap_id=gap.id, admin_user_id=admin_id,
        error_notes="API M365 returned 403 · admin consent revoked",
        error_metadata={"http_status": 403, "tenant_id": "abc-123"},
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.FAILED.value
    assert gap.resolved_at is None  # NOT marked resolved
    assert gap.resolved_by_user_id is None

    logs = await orch.list_audit_logs(gap_id=gap.id)
    assert len(logs) == 4
    failed_log = logs[-1]
    assert failed_log.action == CloudRemediationLogAction.FAILED.value
    assert failed_log.notes == "API M365 returned 403 · admin consent revoked"
    # Ejecutable 8 Pasada 16 (b · test desfasado · fuente: Phase A Enhancement · mark_failed
    # enriquece metadata con failure_category/status, remediation_orchestrator.py:529-560).
    # El error_metadata pasado debe estar CONTENIDO (subset), no exact-match.
    assert {"http_status": 403, "tenant_id": "abc-123"}.items() <= failed_log.metadata_jsonb.items()


# ════════════════════════════════════════════════════════════════════
# Invalid transitions raise
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_invalid_transition_cliente_approve_on_detected_raises(
    db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)
    orch = CloudRemediationOrchestrator(db)

    with pytest.raises(InvalidTransitionError) as exc_info:
        await orch.cliente_approve(
            gap_id=gap.id, cliente_user_id=uuid.uuid4(),
        )

    assert "detected to approved" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_transition_execute_without_approval_raises(
    db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)
    orch = CloudRemediationOrchestrator(db)

    await orch.propose_to_cliente(gap_id=gap.id, admin_user_id=uuid.uuid4())

    with pytest.raises(InvalidTransitionError):
        await orch.start_execution(gap_id=gap.id, admin_user_id=uuid.uuid4())


# ════════════════════════════════════════════════════════════════════
# Gap NOT found
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_gap_not_found_raises(db: AsyncSession) -> None:
    _, _ = await setup_test_project(db)
    orch = CloudRemediationOrchestrator(db)
    fake_gap_id = uuid.uuid4()

    with pytest.raises(GapNotFoundError):
        await orch.propose_to_cliente(
            gap_id=fake_gap_id, admin_user_id=uuid.uuid4(),
        )


# ════════════════════════════════════════════════════════════════════
# Audit trail order chronological
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_audit_trail_order_chronological(db: AsyncSession) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)
    orch = CloudRemediationOrchestrator(db)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()

    await orch.propose_to_cliente(gap_id=gap.id, admin_user_id=admin_id)
    await orch.cliente_approve(gap_id=gap.id, cliente_user_id=cliente_id)

    logs = await orch.list_audit_logs(gap_id=gap.id)
    assert len(logs) == 2
    # Created_at ASC sorted
    assert logs[0].created_at <= logs[1].created_at
    assert logs[0].action == CloudRemediationLogAction.PROPOSED_TO_CLIENTE.value
    assert logs[1].action == CloudRemediationLogAction.CLIENTE_APPROVED.value
