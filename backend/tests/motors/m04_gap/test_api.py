"""Tests HTTP Motor 4 -- Gap Analysis Engine REST API.

Pattern consistent with M19 and M3 test_api.py.
"""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.app.motors.m04_gap.service import FUENTE_GAP
from backend.app.models.findings import Finding
from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1"


async def _setup_dda_project(async_client, db, categoria="BASICA"):
    """Create project + system + categorization + DdA via M3.

    Returns project_id.
    """
    _, project_id = await setup_test_project(db)

    system_id = uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:sid, :pid, 'Test System', now())"
        ), {"sid": str(system_id), "pid": str(project_id)})
        await db.execute(text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, created_at) "
            "VALUES (:id, :sid, :cat, now())"
        ), {"id": str(uuid4()), "sid": str(system_id), "cat": categoria})
    await db.flush()

    # Generate DdA via M3 HTTP endpoint
    r = await async_client.post(
        f"{BASE}/dda/generate",
        json={"project_id": project_id, "system_category": categoria, "responsable": "RSEG"},
    )
    assert r.status_code == 201, f"DdA generate failed: {r.status_code} {r.text}"
    return project_id


async def _create_gap_directly(db, project_id, codigo="org.1"):
    """Create a gap finding directly in DB for CRUD tests."""
    async with _admin_setup(db):
        f = Finding(
            project_id=project_id,
            fuente=FUENTE_GAP,
            severidad="alta",
            medida_afectada=codigo,
            descripcion=f"Gap en {codigo}",
            estado="abierto",
            metadata_jsonb={
                "motor": "m04_gap", "codigo_medida": codigo,
                "familia": "org", "quick_win": False, "nuclear": False,
            },
        )
        db.add(f)
        await db.flush()
    return str(f.id)


class TestAnalyzeEndpoint:

    @pytest.mark.asyncio
    async def test_post_analyze_201(self, async_client, db):
        pid = await _setup_dda_project(async_client, db, "BASICA")
        r = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"force": False, "categoria_objetivo": "BASICA"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["gaps_created"] > 0
        assert data["categoria_usada"] == "BASICA"

    @pytest.mark.asyncio
    async def test_post_analyze_without_dda_409(self, async_client, db):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_post_analyze_force_true(self, async_client, db):
        pid = await _setup_dda_project(async_client, db, "BASICA")
        r1 = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        assert r1.status_code == 201
        count1 = r1.json()["gaps_created"]

        r2 = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"force": True, "categoria_objetivo": "BASICA"},
        )
        assert r2.status_code == 201
        assert r2.json()["gaps_created"] == count1


    @pytest.mark.asyncio
    async def test_post_analyze_already_analyzed_409(self, async_client, db):
        """Double analyze without force returns 409."""
        pid = await _setup_dda_project(async_client, db, "BASICA")
        await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        r = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_post_analyze_invalid_categoria_422(self, async_client, db):
        """Invalid categoria_objetivo returns 422."""
        pid = await _setup_dda_project(async_client, db, "BASICA")
        r = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "INVENTADA"},
        )
        assert r.status_code == 422


class TestCrudEndpoints:

    @pytest.mark.asyncio
    async def test_get_gap_404(self, async_client, db):
        r = await async_client.get(f"{BASE}/gaps/{uuid4()}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_list_gaps_empty_200(self, async_client, db):
        _, pid = await setup_test_project(db)
        r = await async_client.get(f"{BASE}/projects/{pid}/gaps")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_get_list_gaps_with_filters(self, async_client, db):
        pid = await _setup_dda_project(async_client, db, "BASICA")
        await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        r = await async_client.get(
            f"{BASE}/projects/{pid}/gaps?severidad=critica",
        )
        assert r.status_code == 200
        for g in r.json():
            assert g["severidad"] == "critica"

    @pytest.mark.asyncio
    async def test_patch_update_gap_200(self, async_client, db):
        _, pid = await setup_test_project(db)
        gap_id = await _create_gap_directly(db, pid)
        r = await async_client.patch(
            f"{BASE}/gaps/{gap_id}",
            json={"severidad": "critica"},
        )
        assert r.status_code == 200
        assert r.json()["severidad"] == "critica"

    @pytest.mark.asyncio
    async def test_patch_update_gap_invalid_422(self, async_client, db):
        _, pid = await setup_test_project(db)
        gap_id = await _create_gap_directly(db, pid)
        r = await async_client.patch(
            f"{BASE}/gaps/{gap_id}",
            json={"severidad": "inventada"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_gap_204(self, async_client, db):
        _, pid = await setup_test_project(db)
        gap_id = await _create_gap_directly(db, pid)
        r = await async_client.delete(f"{BASE}/gaps/{gap_id}")
        assert r.status_code == 204


class TestLifecycleEndpoint:

    @pytest.mark.asyncio
    async def test_post_close_gap_200(self, async_client, db):
        _, pid = await setup_test_project(db)
        gap_id = await _create_gap_directly(db, pid)
        r = await async_client.post(
            f"{BASE}/gaps/{gap_id}/close",
            json={"resolution_notes": "Fixed", "closed_by": "RSEG"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["estado"] == "cerrado"
        assert data["metadata_jsonb"]["closure"]["resolution_notes"] == "Fixed"

    @pytest.mark.asyncio
    async def test_post_close_gap_already_closed_409(self, async_client, db):
        _, pid = await setup_test_project(db)
        gap_id = await _create_gap_directly(db, pid)
        await async_client.post(
            f"{BASE}/gaps/{gap_id}/close",
            json={"resolution_notes": "Fixed"},
        )
        r = await async_client.post(
            f"{BASE}/gaps/{gap_id}/close",
            json={"resolution_notes": "Again"},
        )
        assert r.status_code == 409


class TestDashboardEndpoints:

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_200(self, async_client, db):
        _, pid = await setup_test_project(db)
        r = await async_client.get(f"{BASE}/projects/{pid}/gaps/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert data["total_gaps"] == 0
        assert data["by_semaforo"] == {"verde": 0, "amarillo": 0, "rojo": 0}

    @pytest.mark.asyncio
    async def test_get_dashboard_with_gaps_200(self, async_client, db):
        pid = await _setup_dda_project(async_client, db, "BASICA")
        await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        r = await async_client.get(f"{BASE}/projects/{pid}/gaps/dashboard")
        assert r.status_code == 200
        assert r.json()["total_gaps"] > 0

    @pytest.mark.asyncio
    async def test_get_quick_wins_200(self, async_client, db):
        pid = await _setup_dda_project(async_client, db, "BASICA")
        await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        r = await async_client.get(f"{BASE}/projects/{pid}/gaps/quick-wins")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_quick_wins_excludes_cerrado(self, async_client, db):
        """Quick-wins endpoint filters out cerrado gaps."""
        _, pid = await setup_test_project(db)
        # Create a quick-win gap and close it
        gap_id = await _create_gap_directly(db, pid, "QW-001")
        # Mark it as quick_win in metadata
        async with _admin_setup(db):
            await db.execute(text(
                "UPDATE findings SET metadata_jsonb = :md WHERE id = :id"
            ), {
                "md": '{"motor":"m04_gap","quick_win":true,"nuclear":false,"familia":"org"}',
                "id": gap_id,
            })
        await db.flush()
        # Close it
        await async_client.post(
            f"{BASE}/gaps/{gap_id}/close",
            json={"resolution_notes": "Done"},
        )
        # Quick wins should be empty (cerrado filtered out)
        r = await async_client.get(f"{BASE}/projects/{pid}/gaps/quick-wins")
        assert r.status_code == 200
        assert len(r.json()) == 0

    @pytest.mark.asyncio
    async def test_analyze_then_list_e2e(self, async_client, db):
        """E2E: POST analyze -> GET list -> gaps visible."""
        pid = await _setup_dda_project(async_client, db, "BASICA")
        r1 = await async_client.post(
            f"{BASE}/projects/{pid}/gaps/analyze",
            json={"categoria_objetivo": "BASICA"},
        )
        assert r1.status_code == 201
        count = r1.json()["gaps_created"]

        r2 = await async_client.get(f"{BASE}/projects/{pid}/gaps")
        assert r2.status_code == 200
        assert len(r2.json()) == count
