"""Tests Bloque 3+5 Enhancement Phase A · Idempotency + VERIFICATION_PENDING + Failure categorization.

Path B refined (OPS-052 13ª manifestation):
  - Sostiene ADR-014 read-only · NO auto-execute capability
  - Audit enrichment + idempotency + lifecycle state expand
  - mark_executed opt-in auto-transition VERIFICATION_PENDING
  - mark_verified · terminal VERIFIED + system_consciousness hook (Phase B)
  - request_rollback · re-enter EXECUTING (admin manual rollback)
  - mark_failed con failure_category + correlation_id
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
    CloudGapSeverity,
    CloudGapType,
    CloudRemediationActorType,
    CloudRemediationApprovalStatus,
    CloudRemediationFailureCategory,
    CloudRemediationLogAction,
)
from backend.app.motors.m_cloud_connectors.remediation_orchestrator import (
    CloudRemediationOrchestrator,
    _ALLOWED_TRANSITIONS,
    _can_transition,
    compute_idempotency_key,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Pure idempotency key generation
# ════════════════════════════════════════════════════════════════════


class TestIdempotencyKeyGeneration:
    """compute_idempotency_key · deterministic SHA-256 (gap_id+action+pre_state)."""

    def test_same_inputs_produce_same_key(self) -> None:
        gid = uuid.uuid4()
        key1 = compute_idempotency_key(gid, "executed", "executing")
        key2 = compute_idempotency_key(gid, "executed", "executing")
        assert key1 == key2

    def test_different_gap_produces_different_key(self) -> None:
        gid1 = uuid.uuid4()
        gid2 = uuid.uuid4()
        key1 = compute_idempotency_key(gid1, "executed", "executing")
        key2 = compute_idempotency_key(gid2, "executed", "executing")
        assert key1 != key2

    def test_different_action_produces_different_key(self) -> None:
        gid = uuid.uuid4()
        key1 = compute_idempotency_key(gid, "executed", "executing")
        key2 = compute_idempotency_key(gid, "failed", "executing")
        assert key1 != key2

    def test_extra_param_changes_key(self) -> None:
        gid = uuid.uuid4()
        key1 = compute_idempotency_key(gid, "executed", "executing")
        key2 = compute_idempotency_key(gid, "executed", "executing", extra="2026-05-25")
        assert key1 != key2

    def test_key_within_varchar_limit(self) -> None:
        gid = uuid.uuid4()
        key = compute_idempotency_key(gid, "executed", "executing")
        assert len(key) <= 128


# ════════════════════════════════════════════════════════════════════
# State machine extended · VERIFICATION_PENDING + VERIFIED
# ════════════════════════════════════════════════════════════════════


class TestStateMachineExtended:
    """Phase A · extended transitions executed → verification_pending → verified."""

    def test_executed_allows_verification_pending(self) -> None:
        assert _can_transition("executed", "verification_pending") is True

    def test_verification_pending_allows_verified(self) -> None:
        assert _can_transition("verification_pending", "verified") is True

    def test_verification_pending_allows_back_to_executing(self) -> None:
        """Rollback path · admin re-corrects."""
        assert _can_transition("verification_pending", "executing") is True

    def test_verified_is_terminal(self) -> None:
        assert _ALLOWED_TRANSITIONS["verified"] == set()

    def test_failed_remains_terminal(self) -> None:
        assert _ALLOWED_TRANSITIONS["failed"] == set()


# ════════════════════════════════════════════════════════════════════
# Helpers DB setup (re-uso pattern existing)
# ════════════════════════════════════════════════════════════════════


async def _create_gap_with_connector(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    *,
    title: str = "Test gap MFA missing",
    severity: str = CloudGapSeverity.CRITICAL.value,
    ens_measure_code: str = "op.acc.6",
) -> CloudGap:
    """Crea CloudConnector + CloudGap para testing."""
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


async def _advance_to_executing(
    orch: CloudRemediationOrchestrator,
    gap: CloudGap,
    admin_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> CloudGap:
    """Helper · advance gap detected → executing."""
    gap = await orch.propose_to_cliente(
        gap_id=gap.id, admin_user_id=admin_id, notes="Crítico",
    )
    gap = await orch.cliente_approve(
        gap_id=gap.id, cliente_user_id=cliente_id,
    )
    gap = await orch.start_execution(
        gap_id=gap.id, admin_user_id=admin_id,
    )
    return gap


# ════════════════════════════════════════════════════════════════════
# Phase A · auto_enter_verification flow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mark_executed_auto_enter_verification_true(
    db: AsyncSession,
) -> None:
    """Phase A · default API behavior · executed → VERIFICATION_PENDING auto."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)

    gap = await orch.mark_executed(
        gap_id=gap.id,
        admin_user_id=admin_id,
        notes="MFA enforced",
        auto_enter_verification=True,
    )

    # State should be VERIFICATION_PENDING after auto-transition
    assert gap.approval_status == CloudRemediationApprovalStatus.VERIFICATION_PENDING.value
    assert gap.verification_pending_at is not None
    assert gap.resolved_at is not None

    # Audit trail · 5 logs (propose + approve + execute + executed + verification_pending)
    logs = await orch.list_audit_logs(gap_id=gap.id)
    assert len(logs) == 5
    assert logs[3].action == CloudRemediationLogAction.EXECUTED.value
    assert logs[4].action == CloudRemediationLogAction.VERIFICATION_PENDING.value
    assert logs[4].actor_type == CloudRemediationActorType.SYSTEM.value


@pytest.mark.asyncio
async def test_mark_executed_auto_enter_verification_false_backward_compat(
    db: AsyncSession,
) -> None:
    """Backward compat · default False preserves executed terminal behavior."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)

    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id, notes="MFA enforced",
        # auto_enter_verification omitted · default False
    )

    # State remains EXECUTED (legacy behavior)
    assert gap.approval_status == CloudRemediationApprovalStatus.EXECUTED.value
    assert gap.verification_pending_at is None


# ════════════════════════════════════════════════════════════════════
# Phase A · mark_verified terminal flow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mark_verified_terminal_state(db: AsyncSession) -> None:
    """verification_pending → verified · TERMINAL · system_consciousness hook fired."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=True,
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.VERIFICATION_PENDING.value

    correlation_id = uuid.uuid4()
    gap = await orch.mark_verified(
        gap_id=gap.id,
        admin_user_id=admin_id,
        notes="MFA confirmed in Azure portal · all 12 users enrolled",
        correlation_id=correlation_id,
    )

    assert gap.approval_status == CloudRemediationApprovalStatus.VERIFIED.value
    assert gap.verified_at is not None
    assert gap.verified_by_user_id == admin_id

    # Audit log VERIFIED action present con correlation_id
    logs = await orch.list_audit_logs(gap_id=gap.id)
    verified_log = next(
        (l for l in logs if l.action == CloudRemediationLogAction.VERIFIED.value),
        None,
    )
    assert verified_log is not None
    assert verified_log.correlation_id == correlation_id
    assert verified_log.metadata_jsonb is not None
    assert "friendly_message" in verified_log.metadata_jsonb
    assert "Marcos confirmó" in verified_log.metadata_jsonb["friendly_message"]


# ════════════════════════════════════════════════════════════════════
# Phase A · request_rollback flow · re-enter executing
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_request_rollback_reenters_executing(db: AsyncSession) -> None:
    """verification_pending → executing (admin re-corrects manual)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=True,
    )
    assert gap.approval_status == CloudRemediationApprovalStatus.VERIFICATION_PENDING.value

    gap = await orch.request_rollback(
        gap_id=gap.id,
        admin_user_id=admin_id,
        reason="Verify check revealed 2 users still without MFA",
    )

    assert gap.approval_status == CloudRemediationApprovalStatus.EXECUTING.value
    assert gap.verification_pending_at is None  # reset

    logs = await orch.list_audit_logs(gap_id=gap.id)
    rollback_log = next(
        (l for l in logs if l.action == CloudRemediationLogAction.ROLLBACK_REQUESTED.value),
        None,
    )
    assert rollback_log is not None
    assert "Verify check revealed" in (rollback_log.notes or "")
    assert "friendly_message" in (rollback_log.metadata_jsonb or {})


# ════════════════════════════════════════════════════════════════════
# Phase A · mark_failed enriched
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mark_failed_with_category_transient(db: AsyncSession) -> None:
    """mark_failed con failure_category=transient + correlation_id."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)

    gap = await orch.mark_failed(
        gap_id=gap.id,
        admin_user_id=admin_id,
        error_notes="Azure API timeout · retry suggested",
        failure_category=CloudRemediationFailureCategory.TRANSIENT.value,
        error_metadata={"http_status": 504, "endpoint": "graph.microsoft.com"},
        correlation_id=correlation_id,
    )

    assert gap.approval_status == CloudRemediationApprovalStatus.FAILED.value

    logs = await orch.list_audit_logs(gap_id=gap.id)
    failed_log = next(
        (l for l in logs if l.action == CloudRemediationLogAction.FAILED.value),
        None,
    )
    assert failed_log is not None
    assert failed_log.failure_category == CloudRemediationFailureCategory.TRANSIENT.value
    assert failed_log.correlation_id == correlation_id
    assert failed_log.metadata_jsonb is not None
    assert failed_log.metadata_jsonb.get("http_status") == 504
    # R29 friendly message embedded
    assert "Marcos encontró un problema" in failed_log.metadata_jsonb["friendly_message"]
    assert "Sin prisa" in failed_log.metadata_jsonb["friendly_message"]


@pytest.mark.asyncio
async def test_mark_failed_invalid_category_falls_back_unknown(
    db: AsyncSession,
) -> None:
    """Invalid failure_category falls back to UNKNOWN safely."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)

    gap = await orch.mark_failed(
        gap_id=gap.id,
        admin_user_id=admin_id,
        error_notes="something went wrong",
        failure_category="nonsense-value",
    )

    logs = await orch.list_audit_logs(gap_id=gap.id)
    failed_log = logs[-1]
    assert failed_log.failure_category == CloudRemediationFailureCategory.UNKNOWN.value


# ════════════════════════════════════════════════════════════════════
# Phase A · Idempotency log behavior
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_idempotency_duplicate_log_returns_existing(
    db: AsyncSession,
) -> None:
    """Mismo (gap_id, action, idempotency_key) tuple · 2nd call returns existing."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)

    # mark_executed twice with same gap (idempotency_key deterministic)
    gap1 = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=False,  # avoid auto-transition for simpler assert
    )
    state_after_first = gap1.approval_status

    # Second call · gap NOW executed · same call SHOULD fail InvalidTransition
    # (executed → executed not allowed) UNLESS idempotency dedup at log level
    # Real test · invoke _record_log directly with same idempotency_key
    key = compute_idempotency_key(
        gap.id, CloudRemediationLogAction.EXECUTED.value, "executing",
    )
    # Try to insert duplicate log with same key
    log1 = await orch._record_log(
        gap=gap1,
        action=CloudRemediationLogAction.EXECUTED.value,
        actor_user_id=admin_id,
        actor_type=CloudRemediationActorType.ADMIN.value,
        idempotency_key=key,
    )
    log2 = await orch._record_log(
        gap=gap1,
        action=CloudRemediationLogAction.EXECUTED.value,
        actor_user_id=admin_id,
        actor_type=CloudRemediationActorType.ADMIN.value,
        idempotency_key=key,
    )
    # Same row returned · NO duplicate
    assert log1.id == log2.id


@pytest.mark.asyncio
async def test_audit_log_includes_pre_post_state_metadata(
    db: AsyncSession,
) -> None:
    """Phase A enriched metadata · pre_state + post_state captured per transition."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap_with_connector(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    orch = CloudRemediationOrchestrator(db)

    gap = await _advance_to_executing(orch, gap, admin_id, cliente_id)
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=False,
    )

    logs = await orch.list_audit_logs(gap_id=gap.id)
    executed_log = next(
        (l for l in logs if l.action == CloudRemediationLogAction.EXECUTED.value),
        None,
    )
    assert executed_log is not None
    md = executed_log.metadata_jsonb or {}
    assert md.get("pre_state") == "executing"
    assert md.get("post_state") == "executed"
