"""Integration tests Bloque 3+5 · cloud_remediation_orchestrator API endpoints.

Cubre:
  - Admin propose-to-cliente · gap transition + log row + JSON response
  - Admin execute · mark-executed · mark-failed flow
  - Admin audit-log endpoint returns chronological logs
  - Admin 404 on unknown gap · 409 on invalid transition
  - Cliente approve · reject · list pending pattern
  - Cliente 403 si gap pertenece a otro project
  - Cliente friendly_message R29 sostained
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
    CloudGap,
    CloudGapType,
    CloudGapSeverity,
    CloudRemediationApprovalStatus,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Fixtures auth bypass
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def authed_admin_client(client: AsyncClient, db: AsyncSession):
    """Pattern reuse · client + admin auth bypass via require_owner."""
    from backend.app.auth.dependencies import require_owner
    from backend.app.main import app

    class _StubUser:
        id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        email = "marcos@fulkro.test"
        is_owner = True

    async def _override_owner():
        return _StubUser()

    app.dependency_overrides[require_owner] = _override_owner
    yield client
    app.dependency_overrides.pop(require_owner, None)


@pytest.fixture
async def authed_client_user(client: AsyncClient, db: AsyncSession):
    """Pattern reuse · cliente auth bypass via require_client_user."""
    from backend.app.auth.dependencies import require_client_user
    from backend.app.main import app

    class _StubClienteUser:
        id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        email = "cliente@example.test"
        client_id = None  # Set per test

    stub = _StubClienteUser()

    async def _override_client():
        return stub

    app.dependency_overrides[require_client_user] = _override_client
    yield client, stub
    app.dependency_overrides.pop(require_client_user, None)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_gap(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    *,
    approval_status: str = CloudRemediationApprovalStatus.DETECTED.value,
    title: str = "Test gap",
    severity: str = CloudGapSeverity.HIGH.value,
) -> CloudGap:
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
            ens_measure_code="op.acc.6",
            title=title,
            suggested_action="Enable MFA",
            auto_fixable=False,
            cliente_can_see=True,
            approval_status=approval_status,
        )
        db.add(gap)
        await db.flush()
    return gap


# ════════════════════════════════════════════════════════════════════
# Admin endpoints
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_propose_to_cliente_happy_path(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid, title="MFA missing")

    response = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/propose-to-cliente",
        json={"notes": "Crítico · MFA bypass detected"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approval_status"] == "proposed_to_cliente"
    assert body["id"] == str(gap.id)
    assert body["proposed_to_cliente_at"] is not None


@pytest.mark.asyncio
async def test_admin_propose_to_cliente_404_unknown_gap(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    fake_gap_id = uuid.uuid4()
    response = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{fake_gap_id}/propose-to-cliente",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_propose_invalid_transition_returns_409(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    # Pre-approved gap · NO permite propose again
    gap = await _create_gap(
        db, project_uuid,
        approval_status=CloudRemediationApprovalStatus.APPROVED.value,
    )

    response = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/propose-to-cliente",
        json={},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_admin_full_flow_then_audit_log(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """Propose → approve manually (DB direct simulate cliente) → execute → mark-executed."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(db, project_uuid)

    # 1. Propose
    r1 = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/propose-to-cliente",
        json={"notes": "step 1"},
    )
    assert r1.status_code == 200

    # 2. Simulate cliente approval direct DB (bypassing cliente auth fixture)
    async with _admin_setup(db):
        from backend.app.motors.m_cloud_connectors.remediation_orchestrator import (
            CloudRemediationOrchestrator,
        )
        orch = CloudRemediationOrchestrator(db)
        await orch.cliente_approve(
            gap_id=gap.id, cliente_user_id=uuid.uuid4(), notes="cliente OK",
        )

    # 3. Start execution
    r3 = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/execute",
        json={"notes": "starting MFA rollout"},
    )
    assert r3.status_code == 200
    assert r3.json()["approval_status"] == "executing"

    # 4. Mark executed
    evidence_id = uuid.uuid4()
    r4 = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/mark-executed",
        json={
            "evidence_link_id": str(evidence_id),
            "notes": "MFA enforced",
        },
    )
    assert r4.status_code == 200
    # Ejecutable 8 Pasada 16 (b · test desfasado · fuente: Phase A Enhancement · mark-executed
    # AUTO-transiciona a verification_pending, remediation_orchestrator.py:94-103 "EXECUTED →
    # VERIFICATION_PENDING (auto)"). Antes era terminal 'executed'.
    assert r4.json()["approval_status"] == "verification_pending"
    assert r4.json()["evidence_link_id"] == str(evidence_id)

    # 5. Audit log
    r5 = await authed_admin_client.get(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/audit-log",
    )
    assert r5.status_code == 200
    body = r5.json()
    # Ejecutable 8 Pasada 16 (b · fuente: Phase A · mark-executed auto-transiciona a
    # verification_pending y registra ambos logs · 4 -> 5).
    assert body["count"] == 5
    actions = [l["action"] for l in body["logs"]]
    assert actions == [
        "proposed_to_cliente",
        "cliente_approved",
        "executing",
        "executed",
        "verification_pending",
    ]


@pytest.mark.asyncio
async def test_admin_mark_failed_with_error_metadata(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    gap = await _create_gap(
        db, project_uuid,
        approval_status=CloudRemediationApprovalStatus.EXECUTING.value,
    )

    response = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}"
        f"/cloud-gaps/{gap.id}/mark-failed",
        json={
            "error_notes": "API M365 403 · admin consent revoked",
            "error_metadata": {"http_status": 403, "tenant_id": "abc"},
        },
    )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "failed"


# ════════════════════════════════════════════════════════════════════
# Cliente endpoints
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cliente_approve_friendly_response(
    authed_client_user, db: AsyncSession,
) -> None:
    client, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    stub.client_id = uuid.UUID(client_id_str)

    gap = await _create_gap(
        db, project_uuid,
        approval_status=CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value,
    )
    # Set proposed timestamp for ordering tests
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE cloud_gaps SET proposed_to_cliente_at = now() "
                "WHERE id = :gid"
            ),
            {"gid": str(gap.id)},
        )

    response = await client.post(
        f"/api/v1/client-portal/cloud-gaps/{gap.id}/approve",
        json={"notes": "OK aprobamos"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approval_status"] == "approved"
    assert "friendly_message" in body
    # R29 firmísimo · friendly Spanish · NO jerga
    assert "Marcos" in body["friendly_message"] or "Gracias" in body["friendly_message"]


@pytest.mark.asyncio
async def test_cliente_reject_friendly_response(
    authed_client_user, db: AsyncSession,
) -> None:
    client, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    stub.client_id = uuid.UUID(client_id_str)

    gap = await _create_gap(
        db, project_uuid,
        approval_status=CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value,
    )

    response = await client.post(
        f"/api/v1/client-portal/cloud-gaps/{gap.id}/reject",
        json={"notes": "Sin presupuesto"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approval_status"] == "rejected"
    assert "friendly_message" in body


@pytest.mark.asyncio
async def test_cliente_cannot_access_other_project_gap_403(
    authed_client_user, db: AsyncSession,
) -> None:
    client, stub = authed_client_user
    # Cliente belongs a project A · intenta acceder gap project B
    client_a_id, project_a_id = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_a_id)

    client_b_id, project_b_id = await setup_test_project(db)
    project_b_uuid = uuid.UUID(project_b_id)
    gap_b = await _create_gap(
        db, project_b_uuid,
        approval_status=CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value,
    )

    response = await client.post(
        f"/api/v1/client-portal/cloud-gaps/{gap_b.id}/approve",
        json={},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cliente_list_pending_remediations_empty(
    authed_client_user, db: AsyncSession,
) -> None:
    client, stub = authed_client_user
    client_id_str, _ = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)

    response = await client.get(
        "/api/v1/client-portal/cloud-gaps",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["gaps"] == []
