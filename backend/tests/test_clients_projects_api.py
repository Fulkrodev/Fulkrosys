"""
Tests for Core — Clients & Projects REST API (HTTP integration tests).
"""
import uuid
import pytest


# ================================================================
# CLIENT TESTS (3 tests)
# ================================================================

class TestClientHTTP:
    """HTTP tests for client endpoints."""

    @pytest.mark.asyncio
    async def test_create_client_returns_201(self, async_client, db):
        """POST /clients devuelve 201 con client_id."""
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        response = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "Test Client", "cif": cif},
        )
        assert response.status_code == 201, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["nombre"] == "Test Client"
        assert data["cif"] == cif

    @pytest.mark.asyncio
    async def test_create_client_duplicate_cif_returns_409(self, async_client, db):
        """POST /clients con CIF duplicado devuelve 409."""
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        r1 = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "First", "cif": cif},
        )
        assert r1.status_code == 201

        r2 = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "Duplicate", "cif": cif},
        )
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_list_clients_returns_array(self, async_client, db):
        """GET /clients devuelve lista."""
        response = await async_client.get("/api/v1/clients")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ================================================================
# PROJECT TESTS (3 tests)
# ================================================================

class TestProjectHTTP:
    """HTTP tests for project endpoints."""

    @pytest.mark.asyncio
    async def test_create_project_returns_201(self, async_client, db):
        """POST /clients/{id}/projects devuelve 201."""
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        cr = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "Test", "cif": cif},
        )
        client_id = cr.json()["id"]

        response = await async_client.post(
            f"/api/v1/clients/{client_id}/projects",
            json={"nombre": "Proyecto ENS", "categoria_objetivo": "MEDIA"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Proyecto ENS"
        assert data["client_id"] == client_id
        assert data["categoria_objetivo"] == "MEDIA"

    @pytest.mark.asyncio
    async def test_create_project_404_if_client_not_found(self, async_client, db):
        """POST /clients/{fake_id}/projects devuelve 404."""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/clients/{fake_id}/projects",
            json={"nombre": "Test"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_projects_of_client_returns_array(self, async_client, db):
        """GET /clients/{id}/projects devuelve lista."""
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        cr = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "Test", "cif": cif},
        )
        client_id = cr.json()["id"]

        # Create a project first
        await async_client.post(
            f"/api/v1/clients/{client_id}/projects",
            json={"nombre": "P1"},
        )

        response = await async_client.get(f"/api/v1/clients/{client_id}/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["nombre"] == "P1"


# ================================================================
# Sub-atom 1.E.2.bis Phase A · Project soft delete (archive) tests
# ================================================================


class TestArchiveProjectHTTP:
    """DELETE /api/v1/clients/{id}/projects/{pid} · soft delete pattern."""

    @pytest.mark.asyncio
    async def test_archive_project_sets_lifecycle_archived(
        self, async_client, db,
    ):
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        cr = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "Archive Test", "cif": cif},
        )
        client_id = cr.json()["id"]

        pr = await async_client.post(
            f"/api/v1/clients/{client_id}/projects",
            json={"nombre": "P-archivable", "categoria_objetivo": "MEDIA"},
        )
        project_id = pr.json()["id"]

        response = await async_client.delete(
            f"/api/v1/clients/{client_id}/projects/{project_id}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lifecycle_state"] == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_archive_project_idempotent(self, async_client, db):
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        cr = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "Idem Test", "cif": cif},
        )
        client_id = cr.json()["id"]
        pr = await async_client.post(
            f"/api/v1/clients/{client_id}/projects",
            json={"nombre": "P-idem"},
        )
        project_id = pr.json()["id"]

        r1 = await async_client.delete(
            f"/api/v1/clients/{client_id}/projects/{project_id}",
        )
        r2 = await async_client.delete(
            f"/api/v1/clients/{client_id}/projects/{project_id}",
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["lifecycle_state"] == "ARCHIVED"
        assert r2.json()["lifecycle_state"] == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_archive_project_404_if_not_found(self, async_client, db):
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
        cr = await async_client.post(
            "/api/v1/clients",
            json={"nombre": "404 Test", "cif": cif},
        )
        client_id = cr.json()["id"]
        fake_pid = str(uuid.uuid4())

        response = await async_client.delete(
            f"/api/v1/clients/{client_id}/projects/{fake_pid}",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_archive_project_404_if_wrong_client(self, async_client, db):
        cif1 = f"B{uuid.uuid4().hex[:8].upper()}"
        cif2 = f"B{uuid.uuid4().hex[:8].upper()}"
        c1 = await async_client.post(
            "/api/v1/clients", json={"nombre": "C1", "cif": cif1},
        )
        c2 = await async_client.post(
            "/api/v1/clients", json={"nombre": "C2", "cif": cif2},
        )
        client_1 = c1.json()["id"]
        client_2 = c2.json()["id"]

        pr = await async_client.post(
            f"/api/v1/clients/{client_1}/projects", json={"nombre": "P1"},
        )
        project_1 = pr.json()["id"]

        response = await async_client.delete(
            f"/api/v1/clients/{client_2}/projects/{project_1}",
        )
        assert response.status_code == 404
