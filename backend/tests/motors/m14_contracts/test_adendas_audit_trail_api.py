"""Tests FASE C Phase B · list adendas + audit trail endpoints.

Cubre:
  - GET /providers/adendas project-scoped listing
  - POST /providers/adenda/check admin manual trigger (con/sin template_id custom)

Mock strategy: usa endpoints HTTP reales via TestClient + setup_test_project +
patched AdendaGenerator.generate para evitar MinIO real.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.m14_providers import Provider, ProviderAddendum
from backend.app.motors.m14_contracts.adenda_generator import (
    AdendaGenerationResult,
    TEMPLATE_CODE,
)
from backend.tests.conftest import _admin_setup, setup_test_project


def _make_mock_result(addendum_id: uuid.UUID, code: str) -> AdendaGenerationResult:
    now = datetime.now(timezone.utc)
    return AdendaGenerationResult(
        addendum_id=addendum_id,
        addendum_code=code,
        minio_object_key=f"corpus/addendums/mock/{code}.docx",
        signed_url=f"https://mock-minio/{code}.docx",
        signed_url_expires_at=now,
        normativas_cubiertas=["ENS"],
        docx_size_bytes=20000,
        generated_at=now,
        template_code=TEMPLATE_CODE,
    )


async def _create_provider_and_adenda(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    addendum_code: str,
    audit_trail_metadata: dict | None = None,
    firmado_cliente: bool = False,
) -> tuple[Provider, ProviderAddendum]:
    async with _admin_setup(db):
        provider = Provider(
            project_id=project_id,
            name=f"Provider {addendum_code}",
            type="cloud",
            scope="test scope",
            criticality="CRITICO",
        )
        db.add(provider)
        await db.flush()

        addendum = ProviderAddendum(
            project_id=project_id,
            provider_id=provider.id,
            addendum_code=addendum_code,
            normativas_cubiertas=["ENS", "RGPD"],
            generated_from_template_code=TEMPLATE_CODE,
            firmado_cliente=firmado_cliente,
            metadata_=audit_trail_metadata or {},
        )
        db.add(addendum)
        await db.flush()
    return provider, addendum


# ════════════════════════════════════════════════════════════════════
# Test client wiring · pattern reuse de otros tests M14
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def authed_admin_client(client: AsyncClient, db: AsyncSession):
    """Pattern reuse · client + admin auth bypass."""
    from backend.app.auth.dependencies import require_owner
    from backend.app.main import app

    class _StubUser:
        id = "00000000-0000-0000-0000-000000000001"
        email = "marcos@fulkro.test"
        is_owner = True

    async def _override_owner():
        return _StubUser()

    app.dependency_overrides[require_owner] = _override_owner
    yield client
    app.dependency_overrides.pop(require_owner, None)


# ════════════════════════════════════════════════════════════════════
# GET /providers/adendas tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_project_adendas_empty(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id = await setup_test_project(db)

    response = await authed_admin_client.get(
        f"/api/v1/projects/{project_id}/providers/adendas",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["adendas"] == []


@pytest.mark.asyncio
async def test_list_project_adendas_with_audit_trail(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    # Adenda 1: con audit trail completo workflow + cascade
    _, addendum1 = await _create_provider_and_adenda(
        db,
        project_uuid,
        addendum_code="ADENDA-ENS-2026-0001",
        audit_trail_metadata={
            "last_trigger": "materiality_material_cascade",
            "last_auto_generated_at": "2026-05-24T10:00:00+00:00",
            "triggers_history": [
                {
                    "trigger": "workflow_step_completed",
                    "completed_template_id": "ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL",
                    "auto_generated_at": "2026-05-23T15:00:00+00:00",
                },
                {
                    "trigger": "materiality_material_cascade",
                    "materiality_change_id": str(uuid.uuid4()),
                    "materiality_level": "MATERIAL",
                    "materiality_flags_triggered": ["overlay", "renewal"],
                    "auto_generated_at": "2026-05-24T10:00:00+00:00",
                },
            ],
        },
        firmado_cliente=True,
    )

    # Adenda 2: admin manual con 1 entry
    _, addendum2 = await _create_provider_and_adenda(
        db,
        project_uuid,
        addendum_code="ADENDA-ENS-2026-0002",
        audit_trail_metadata={
            "last_trigger": "admin_manual",
            "last_auto_generated_at": "2026-05-24T11:30:00+00:00",
            "triggers_history": [{
                "trigger": "admin_manual",
                "admin_user_id": "marcos-user-id",
                "auto_generated_at": "2026-05-24T11:30:00+00:00",
            }],
        },
    )

    # Adenda 3: sin metadata (manual legacy pre-FASE C)
    _, addendum3 = await _create_provider_and_adenda(
        db,
        project_uuid,
        addendum_code="ADENDA-ENS-2026-0003",
        audit_trail_metadata=None,
    )

    response = await authed_admin_client.get(
        f"/api/v1/projects/{project_id_str}/providers/adendas",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3

    by_code = {a["addendum_code"]: a for a in body["adendas"]}

    # Verify audit trail visibility per entry
    cascade = by_code["ADENDA-ENS-2026-0001"]
    assert cascade["audit_trail"]["last_trigger"] == "materiality_material_cascade"
    assert len(cascade["audit_trail"]["triggers_history"]) == 2
    assert cascade["firmado_cliente"] is True

    manual = by_code["ADENDA-ENS-2026-0002"]
    assert manual["audit_trail"]["last_trigger"] == "admin_manual"
    assert manual["audit_trail"]["triggers_history"][0]["admin_user_id"] == "marcos-user-id"

    legacy = by_code["ADENDA-ENS-2026-0003"]
    assert legacy["audit_trail"]["last_trigger"] == "manual"  # default fallback
    assert legacy["audit_trail"]["triggers_history"] == []

    # Verify normativas surface
    for entry in body["adendas"]:
        assert "ENS" in entry["normativas_cubiertas"]
        assert "RGPD" in entry["normativas_cubiertas"]


# ════════════════════════════════════════════════════════════════════
# POST /providers/adenda/check admin trigger tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_check_no_providers_returns_empty(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id = await setup_test_project(db)

    response = await authed_admin_client.post(
        f"/api/v1/projects/{project_id}/providers/adenda/check",
        json={},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["adendas_processed"] == 0
    assert body["details"] == []
    assert body["trigger_template_id"] == "ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER"


@pytest.mark.asyncio
async def test_admin_check_custom_template_id_propagated(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    # Create 1 provider + pre-create addendum to mock generation returning it
    _, addendum = await _create_provider_and_adenda(
        db,
        project_uuid,
        addendum_code="ADENDA-ENS-2026-0050",
    )

    mock_result = _make_mock_result(addendum.id, addendum.addendum_code)
    mock_gen = AsyncMock(return_value=mock_result)

    with patch(
        "backend.app.motors.m14_contracts.adenda_generator.AdendaGenerator.generate",
        mock_gen,
    ):
        response = await authed_admin_client.post(
            f"/api/v1/projects/{project_id_str}/providers/adenda/check",
            json={"completed_template_id": "ARCHETYPE_SAAS_ONLY_OP_EXT_CHECKLIST"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["trigger_template_id"] == "ARCHETYPE_SAAS_ONLY_OP_EXT_CHECKLIST"
    assert body["adendas_processed"] == 1
    assert len(body["details"]) == 1
    assert body["details"][0]["trigger"] == "admin_manual"
