"""Tests HTTP Motor 19 -- Project Risk Management REST API.

Patron consistente con M3 DdA Engine test_m03_api.py.
Uses httpx.AsyncClient with FastAPI app + shared DB session.
"""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1"


async def _create_risk_http(async_client, db, project_id=None, **overrides):
    """Create a project + risk via HTTP. Returns (project_id, risk_data)."""
    if project_id is None:
        _, project_id = await setup_test_project(db)

    body = {
        "risk_code": overrides.pop("risk_code", "T-001"),
        "titulo": overrides.pop("titulo", "Test risk"),
        "descripcion": overrides.pop("descripcion", "Test desc"),
        "categoria": overrides.pop("categoria", "tecnico"),
        "probabilidad": overrides.pop("probabilidad", 0.5),
        "impacto_dias": overrides.pop("impacto_dias", 10),
        "owner": overrides.pop("owner", "Marcos"),
    }
    body.update(overrides)

    r = await async_client.post(
        f"{BASE}/projects/{project_id}/risks",
        json=body,
    )
    assert r.status_code == 201, f"Create failed: {r.status_code} {r.text}"
    return project_id, r.json()


class TestCreateEndpoint:

    @pytest.mark.asyncio
    async def test_post_create_risk_201(self, async_client, db):
        """H1: POST create risk returns 201 with ProjectRiskOut."""
        pid, data = await _create_risk_http(async_client, db)
        assert data["risk_code"] == "T-001"
        assert data["status"] == "identificado"
        assert "id" in data
        assert data["project_id"] == pid

    @pytest.mark.asyncio
    async def test_post_create_risk_invalid_data_422(self, async_client, db):
        """H2: Invalid data returns 422."""
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/risks",
            json={"risk_code": "X-001", "titulo": "Bad", "categoria": "inventada"},
        )
        assert r.status_code == 422


class TestGetEndpoints:

    @pytest.mark.asyncio
    async def test_get_risk_404_when_not_exists(self, async_client, db):
        """H3: GET nonexistent risk returns 404."""
        r = await async_client.get(f"{BASE}/risks/{uuid4()}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_list_risks_empty_returns_200(self, async_client, db):
        """H4: GET list risks on empty project returns 200 with empty list."""
        _, project_id = await setup_test_project(db)
        r = await async_client.get(f"{BASE}/projects/{project_id}/risks")
        assert r.status_code == 200
        assert r.json() == []


class TestUpdateDeleteEndpoints:

    @pytest.mark.asyncio
    async def test_patch_update_risk_200(self, async_client, db):
        """H5: PATCH update risk returns 200."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        r = await async_client.patch(
            f"{BASE}/risks/{risk_id}",
            json={"titulo": "Updated via API"},
        )
        assert r.status_code == 200
        assert r.json()["titulo"] == "Updated via API"

    @pytest.mark.asyncio
    async def test_delete_risk_204(self, async_client, db):
        """H6: DELETE risk returns 204 (soft delete)."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        r = await async_client.delete(f"{BASE}/risks/{risk_id}")
        assert r.status_code == 204

        # Verify it's gone
        r2 = await async_client.get(f"{BASE}/risks/{risk_id}")
        assert r2.status_code == 404


class TestLifecycleEndpoints:

    @pytest.mark.asyncio
    async def test_post_monitor_risk_200_with_notas(self, async_client, db):
        """H7: POST monitor transitions to monitorizado with notas."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        r = await async_client.post(
            f"{BASE}/risks/{risk_id}/monitor",
            json={"notas": "Watching closely"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "monitorizado"

    @pytest.mark.asyncio
    async def test_post_materialize_risk_200_evidence(self, async_client, db):
        """H8: POST materialize writes to materialization_evidence field."""
        pid, risk_data = await _create_risk_http(
            async_client, db,
            contingency_plan={"original": "plan"},
        )
        risk_id = risk_data["id"]

        # First monitor
        await async_client.post(
            f"{BASE}/risks/{risk_id}/monitor", json={},
        )
        # Then materialize
        r = await async_client.post(
            f"{BASE}/risks/{risk_id}/materialize",
            json={"trigger_evidence": "Sprint blocked", "materialized_by": "Marcos"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "materializado"
        # CRITICAL: contingency_plan intact, materialization_evidence populated
        assert data["contingency_plan"] == {"original": "plan"}
        assert data["materialization_evidence"]["trigger_evidence"] == "Sprint blocked"

    @pytest.mark.asyncio
    async def test_post_close_risk_200_evidence(self, async_client, db):
        """H9: POST close writes to closure_evidence field."""
        pid, risk_data = await _create_risk_http(
            async_client, db,
            mitigation_plan={"original": "mitigation"},
        )
        risk_id = risk_data["id"]
        r = await async_client.post(
            f"{BASE}/risks/{risk_id}/close",
            json={"resolution_notes": "Resolved", "closed_by": "RSEG"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "cerrado"
        # CRITICAL: mitigation_plan intact, closure_evidence populated
        assert data["mitigation_plan"] == {"original": "mitigation"}
        assert data["closure_evidence"]["resolution_notes"] == "Resolved"


    @pytest.mark.asyncio
    async def test_post_monitor_wrong_status_409(self, async_client, db):
        """H7b: Monitor from monitorizado returns 409."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        # First monitor succeeds
        await async_client.post(f"{BASE}/risks/{risk_id}/monitor", json={})
        # Second monitor fails
        r = await async_client.post(f"{BASE}/risks/{risk_id}/monitor", json={})
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_post_materialize_wrong_status_409(self, async_client, db):
        """H8b: Materialize from identificado returns 409."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        r = await async_client.post(
            f"{BASE}/risks/{risk_id}/materialize",
            json={"trigger_evidence": "test"},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_post_close_from_cerrado_409(self, async_client, db):
        """H9b: Close from cerrado returns 409."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        # Close once
        await async_client.post(
            f"{BASE}/risks/{risk_id}/close",
            json={"resolution_notes": "done"},
        )
        # Try close again
        r = await async_client.post(
            f"{BASE}/risks/{risk_id}/close",
            json={"resolution_notes": "again"},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_patch_update_invalid_categoria_422(self, async_client, db):
        """H5b: PATCH with invalid categoria returns 422."""
        pid, risk_data = await _create_risk_http(async_client, db)
        risk_id = risk_data["id"]
        r = await async_client.patch(
            f"{BASE}/risks/{risk_id}",
            json={"categoria": "inventada"},
        )
        assert r.status_code == 422


class TestCatalogEndpoints:

    @pytest.mark.asyncio
    async def test_post_instantiate_catalog_201(self, async_client, db):
        """H10: POST instantiate-catalog returns 201 with 30 created."""
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/risks/instantiate-catalog",
            json={"force": False},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["risks_created"] == 30

    @pytest.mark.asyncio
    async def test_post_instantiate_catalog_already_loaded_409(self, async_client, db):
        """H11: Double instantiate returns 409."""
        _, project_id = await setup_test_project(db)
        await async_client.post(
            f"{BASE}/projects/{project_id}/risks/instantiate-catalog",
            json={"force": False},
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/risks/instantiate-catalog",
            json={"force": False},
        )
        assert r.status_code == 409


    @pytest.mark.asyncio
    async def test_get_catalog_status_false(self, async_client, db):
        """H11b: Catalog status returns false for fresh project."""
        _, project_id = await setup_test_project(db)
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/risks/catalog-status",
        )
        assert r.status_code == 200
        assert r.json()["instantiated"] is False

    @pytest.mark.asyncio
    async def test_get_catalog_status_true_after_instantiation(self, async_client, db):
        """H11c: Catalog status returns true after instantiation."""
        _, project_id = await setup_test_project(db)
        await async_client.post(
            f"{BASE}/projects/{project_id}/risks/instantiate-catalog",
            json={"force": False},
        )
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/risks/catalog-status",
        )
        assert r.status_code == 200
        assert r.json()["instantiated"] is True


class TestDashboardEndpoint:

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_project_returns_200_with_zeros(self, async_client, db):
        """H12 CRITICAL: Empty project returns 200 dashboard with zeros, NOT 404."""
        _, project_id = await setup_test_project(db)
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/risks/dashboard",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_risks"] == 0
        assert data["by_semaforo"] == {"verde": 0, "amarillo": 0, "rojo": 0}
