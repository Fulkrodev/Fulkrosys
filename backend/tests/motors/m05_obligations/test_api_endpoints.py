"""Tests for Motor 5 -- Obligations REST API endpoints.

Uses ``async_client`` fixture (httpx + ASGI transport) and ``db`` fixture
from conftest.py.  Pattern consistent with M04 Gap test_api.py.
"""
from __future__ import annotations

import uuid

import pytest

from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1"


async def _setup_project_with_ens(async_client, db):
    """Create a project suitable for obligation instantiation.

    Returns project_id (str).
    """
    _, project_id = await setup_test_project(db)
    return project_id


async def _instantiate_org1(async_client, db, project_id: str):
    """Instantiate org.1 obligations via the API and return the response."""
    return await async_client.post(
        f"{BASE}/projects/{project_id}/obligations/instantiate",
        json={
            "nombre_proyecto": "Test Project",
            "categoria_ens": "MEDIA",
            "cliente": {"razon_social": "API Test S.L.", "sector": "tech"},
            "gaps": [
                {"gap_id": str(uuid.uuid4()), "measure_code": "org.1"},
            ],
            "use_llm_personalization": False,
        },
    )


class TestInstantiateEndpoint:

    @pytest.mark.asyncio
    async def test_post_instantiate_200(self, async_client, db):
        """POST instantiate returns 200 with outcomes."""
        project_id = await _setup_project_with_ens(async_client, db)
        r = await _instantiate_org1(async_client, db, project_id)
        assert r.status_code == 200
        data = r.json()
        assert data["total_created"] > 0
        assert "outcomes" in data
        assert len(data["outcomes"]) == 1
        assert data["outcomes"][0]["measure_code"] == "org.1"


class TestGanttEndpoint:

    @pytest.mark.asyncio
    async def test_get_gantt_json_200(self, async_client, db):
        """GET gantt json returns 200 with tareas."""
        project_id = await _setup_project_with_ens(async_client, db)
        r_inst = await _instantiate_org1(async_client, db, project_id)
        assert r_inst.status_code == 200

        r = await async_client.get(
            f"{BASE}/projects/{project_id}/obligations/gantt",
            params={
                "fecha_kickoff": "2025-01-06",
                "dedicacion_horas_semana": 8.0,
                "format": "json",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "tareas" in data
        assert len(data["tareas"]) > 0
        assert "fecha_kickoff" in data

    @pytest.mark.asyncio
    async def test_get_gantt_xlsx_200(self, async_client, db):
        """GET gantt xlsx returns 200 with correct content-type."""
        project_id = await _setup_project_with_ens(async_client, db)
        await _instantiate_org1(async_client, db, project_id)

        r = await async_client.get(
            f"{BASE}/projects/{project_id}/obligations/gantt",
            params={
                "fecha_kickoff": "2025-01-06",
                "format": "xlsx",
            },
        )
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
        # XLSX files are ZIP archives: PK magic bytes
        assert r.content[:2] == b"PK"

    @pytest.mark.asyncio
    async def test_get_gantt_empty_project_200(self, async_client, db):
        """GET gantt for empty project returns 200 with empty tareas."""
        project_id = await _setup_project_with_ens(async_client, db)

        r = await async_client.get(
            f"{BASE}/projects/{project_id}/obligations/gantt",
            params={"fecha_kickoff": "2025-01-06", "format": "json"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tareas"] == []
        assert data["duracion_total_dias_laborables"] == 0
