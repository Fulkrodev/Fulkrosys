"""Tests Bloque 3+5 Enhancement Phase B · System Consciousness cross-module propagation.

Path B refined sostained · ADR-014 read-only · cross-module updates só
metadata + tracking · cloud state unchanged.

Cubre best-effort dispatch pattern:
  - mark_verified() invokes _maybe_dispatch_system_consciousness internally
  - system_consciousness_hooks.maybe_dispatch_remediation_verified() public entry
  - Sub-systems: compliance recheck · dossier evidence · adenda material check
  - SSE dashboards refresh · NotificationOrchestrator cross-stakeholders
  - Audit log propagation summary persisted
  - Graceful degradation · falla en sub-system NO bloquea VERIFIED transition
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
    CloudRemediationApprovalStatus,
    CloudRemediationLogAction,
)
from backend.app.motors.m_cloud_connectors.remediation_orchestrator import (
    CloudRemediationOrchestrator,
)
from backend.app.motors.m_cloud_connectors.system_consciousness_hooks import (
    maybe_dispatch_remediation_verified,
    _maybe_trigger_adenda_if_material,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers (re-uso pattern existing)


async def _create_gap(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    *,
    severity: str = CloudGapSeverity.CRITICAL.value,
    ens_measure_code: str = "op.acc.6",
) -> CloudGap:
    """Crea CloudConnector + CloudGap simple."""
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
            title=f"Test gap {ens_measure_code}",
            suggested_action="Apply fix",
            auto_fixable=False,
            cliente_can_see=True,
        )
        db.add(gap)
        await db.flush()
    return gap


async def _advance_to_verified(
    db: AsyncSession,
    gap: CloudGap,
    admin_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> CloudGap:
    """Helper · advance gap detected → verified."""
    orch = CloudRemediationOrchestrator(db)
    gap = await orch.propose_to_cliente(
        gap_id=gap.id, admin_user_id=admin_id,
    )
    gap = await orch.cliente_approve(
        gap_id=gap.id, cliente_user_id=cliente_id,
    )
    gap = await orch.start_execution(
        gap_id=gap.id, admin_user_id=admin_id,
    )
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=True,
    )
    gap = await orch.mark_verified(
        gap_id=gap.id, admin_user_id=admin_id,
        notes="Verified in cloud console",
    )
    return gap


# ════════════════════════════════════════════════════════════════════
# Pure function tests · adenda material change heurística


@pytest.mark.asyncio
async def test_adenda_skipped_when_not_op_ext(db: AsyncSession) -> None:
    """ENS measure NO op.ext.* · adenda NO triggered."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid, ens_measure_code="op.acc.6")

    correlation_id = uuid.uuid4()
    result = await _maybe_trigger_adenda_if_material(db, gap, correlation_id)

    assert result["status"] == "skipped"
    assert result["reason"] == "not_material_change"
    assert result["ens_measure_code"] == "op.acc.6"


@pytest.mark.asyncio
async def test_adenda_skipped_when_low_severity(db: AsyncSession) -> None:
    """Severity LOW · adenda NO triggered aunque sea op.ext.*."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(
        db, project_uuid,
        severity=CloudGapSeverity.LOW.value,
        ens_measure_code="op.ext.1",
    )

    correlation_id = uuid.uuid4()
    result = await _maybe_trigger_adenda_if_material(db, gap, correlation_id)

    assert result["status"] == "skipped"
    assert result["reason"] == "not_material_change"
    assert result["severity"] == "low"


# ════════════════════════════════════════════════════════════════════
# Integration test · mark_verified triggers propagation hook


@pytest.mark.asyncio
async def test_mark_verified_triggers_propagation_hook(
    db: AsyncSession,
) -> None:
    """mark_verified invokes system_consciousness_hooks · best-effort propagation.

    Verifica que:
    - State transition VERIFIED OK
    - Audit log propagation_summary persisted con subsystems metadata
    - NO exception bubbled (best-effort pattern)
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()

    gap = await _advance_to_verified(db, gap, admin_id, cliente_id)

    assert gap.approval_status == CloudRemediationApprovalStatus.VERIFIED.value

    orch = CloudRemediationOrchestrator(db)
    logs = await orch.list_audit_logs(gap_id=gap.id)
    # 6 logs expected: propose + approve + execute + executed + verification_pending + verified
    # + propagation_summary (best-effort · NOT counted in list if uses non-enum action)
    # Filter audit logs including NOT canonical actions
    propagation_logs = [l for l in logs if l.action == "propagation_summary"]
    assert len(propagation_logs) == 1
    propagation_log = propagation_logs[0]
    assert propagation_log.metadata_jsonb is not None
    assert "subsystems" in propagation_log.metadata_jsonb
    assert "gap_id" in propagation_log.metadata_jsonb
    assert propagation_log.metadata_jsonb["gap_id"] == str(gap.id)


@pytest.mark.asyncio
async def test_propagation_hook_graceful_when_subsystems_fail(
    db: AsyncSession,
) -> None:
    """All sub-systems pueden fallar individually · propagation result captures errors.

    Pattern best-effort · primary VERIFIED transition NUNCA reverted.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid)

    admin_id = uuid.uuid4()
    correlation_id = uuid.uuid4()

    # Advance to verification_pending manually
    orch = CloudRemediationOrchestrator(db)
    cliente_id = uuid.uuid4()
    gap = await orch.propose_to_cliente(gap_id=gap.id, admin_user_id=admin_id)
    gap = await orch.cliente_approve(gap_id=gap.id, cliente_user_id=cliente_id)
    gap = await orch.start_execution(gap_id=gap.id, admin_user_id=admin_id)
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=True,
    )

    # Set verified state for testing dispatcher directly
    gap.approval_status = CloudRemediationApprovalStatus.VERIFIED.value
    from datetime import datetime, timezone
    gap.verified_at = datetime.now(timezone.utc)
    gap.verified_by_user_id = admin_id
    await db.flush()

    # Invoke propagation directly · expect dict result · NO exception bubbled
    result = await maybe_dispatch_remediation_verified(
        db=db,
        gap=gap,
        admin_user_id=admin_id,
        correlation_id=correlation_id,
    )

    assert isinstance(result, dict)
    assert result["gap_id"] == str(gap.id)
    assert result["project_id"] == str(gap.project_id)
    assert result["correlation_id"] == str(correlation_id)
    assert "subsystems" in result
    # Sub-systems present (each con status field)
    subsystems = result["subsystems"]
    for sub in [
        "compliance_recheck",
        "dossier_evidence",
        "adenda_material_check",
        "dashboards_refresh",
        "notifications",
    ]:
        assert sub in subsystems
        assert isinstance(subsystems[sub], dict)


@pytest.mark.asyncio
async def test_verified_primary_transition_succeeds_despite_hook_errors(
    db: AsyncSession,
) -> None:
    """Sostiene 3-point commitment · primary VERIFIED state SOSTAINED aunque hook falla.

    Sub-systems NO disponibles (motors imports fail · APIs not exposed) · gap
    transitions to VERIFIED OK + audit log persisted.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()

    gap = await _advance_to_verified(db, gap, admin_id, cliente_id)

    # PRIMARY transition succeeded · audit log present
    assert gap.approval_status == CloudRemediationApprovalStatus.VERIFIED.value
    assert gap.verified_at is not None
    assert gap.verified_by_user_id == admin_id

    orch = CloudRemediationOrchestrator(db)
    logs = await orch.list_audit_logs(gap_id=gap.id)
    verified_log = next(
        (l for l in logs if l.action == CloudRemediationLogAction.VERIFIED.value),
        None,
    )
    assert verified_log is not None  # Primary audit log present


# ════════════════════════════════════════════════════════════════════
# Cross-system propagation visible in audit metadata


@pytest.mark.asyncio
async def test_propagation_metadata_includes_all_5_subsystems(
    db: AsyncSession,
) -> None:
    """Propagation summary captures 5 sub-system results per ENAC trazabilidad."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()

    gap = await _advance_to_verified(db, gap, admin_id, cliente_id)

    orch = CloudRemediationOrchestrator(db)
    logs = await orch.list_audit_logs(gap_id=gap.id)
    propagation_log = next(
        (l for l in logs if l.action == "propagation_summary"),
        None,
    )
    assert propagation_log is not None
    md = propagation_log.metadata_jsonb or {}
    subsystems = md.get("subsystems", {})

    # All 5 sub-systems present
    expected_subs = {
        "compliance_recheck",
        "dossier_evidence",
        "adenda_material_check",
        "dashboards_refresh",
        "notifications",
    }
    assert expected_subs <= set(subsystems.keys())


@pytest.mark.asyncio
async def test_correlation_id_propagates_through_audit_trail(
    db: AsyncSession,
) -> None:
    """correlation_id persists cross all logs verified + propagation_summary."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid)

    admin_id = uuid.uuid4()
    cliente_id = uuid.uuid4()
    correlation_id = uuid.uuid4()

    orch = CloudRemediationOrchestrator(db)
    gap = await orch.propose_to_cliente(gap_id=gap.id, admin_user_id=admin_id)
    gap = await orch.cliente_approve(gap_id=gap.id, cliente_user_id=cliente_id)
    gap = await orch.start_execution(gap_id=gap.id, admin_user_id=admin_id)
    gap = await orch.mark_executed(
        gap_id=gap.id, admin_user_id=admin_id,
        auto_enter_verification=True, correlation_id=correlation_id,
    )
    gap = await orch.mark_verified(
        gap_id=gap.id, admin_user_id=admin_id,
        correlation_id=correlation_id,
    )

    logs = await orch.list_audit_logs(gap_id=gap.id)
    verified_log = next(
        (l for l in logs if l.action == CloudRemediationLogAction.VERIFIED.value),
        None,
    )
    propagation_log = next(
        (l for l in logs if l.action == "propagation_summary"),
        None,
    )
    assert verified_log is not None
    assert propagation_log is not None
    assert verified_log.correlation_id == correlation_id
    # Propagation log carries SAME correlation_id (via metadata + column)
    assert propagation_log.correlation_id == correlation_id
