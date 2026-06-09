"""Tests HTTP Motor 6 -- Document Factory REST API.

Pattern consistent with M4 and M19 test_api.py.
"""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup

BASE = "/api/v1"


async def _sync_catalog_http(async_client):
    """Sync catalog via HTTP."""
    r = await async_client.post(f"{BASE}/templates/sync-catalog")
    assert r.status_code == 200, f"Sync failed: {r.status_code} {r.text}"
    return r.json()


async def _generate_doc_http(async_client, db, project_id=None, codigo="E-100"):
    """Generate a document via HTTP. Returns (project_id, response_json)."""
    if project_id is None:
        _, project_id = await setup_test_project(db)
    await _sync_catalog_http(async_client)
    ctx = {
        "cliente": {
            "razon_social": "Test Corp",
            "nif": "B12345678",
            "organo_aprobador_politicas": "Comite de Seguridad",
            "domicilio_social": "Calle Test 1, Madrid",
            "persona_contacto": {"nombre": "Juan Perez", "cargo": "CTO"},
        },
        "proyecto": {
            "fecha_aprobacion_inicial": "2026-01-01",
            "version_actual": "1.0",
            "codigo_documento_base": "E-100",
        },
        "responsables": {
            "responsable_seguridad": {"nombre": "Ana Garcia", "cargo": "CISO"},
        },
        "marcos": {"nif": "12345678A"},
        "propuesta": {"fecha_emision": "2026-01-01"},
        "contrato": {"fecha_firma": "2026-01-01", "honorarios_eur": "5000"},
    }
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/documents/generate",
        json={
            "template_codigo": codigo,
            "context": ctx,
            "generate_pdf": False,
            "sign": False,
        },
    )
    return project_id, r


class TestTemplateEndpoints:

    @pytest.mark.asyncio
    async def test_get_templates_list_200(self, async_client, db):
        await _sync_catalog_http(async_client)
        r = await async_client.get(f"{BASE}/templates")
        assert r.status_code == 200
        assert len(r.json()) >= 60

    @pytest.mark.asyncio
    async def test_get_template_by_codigo_200(self, async_client, db):
        await _sync_catalog_http(async_client)
        r = await async_client.get(f"{BASE}/templates/E-100")
        assert r.status_code == 200
        assert r.json()["codigo"] == "E-100"

    @pytest.mark.asyncio
    async def test_get_template_not_found_404(self, async_client, db):
        r = await async_client.get(f"{BASE}/templates/FAKE-999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_post_sync_catalog_200(self, async_client, db):
        r = await async_client.post(f"{BASE}/templates/sync-catalog")
        assert r.status_code == 200
        data = r.json()
        assert "created" in data or "updated" in data


    @pytest.mark.asyncio
    async def test_post_sync_catalog_returns_counters(self, async_client, db):
        r = await async_client.post(f"{BASE}/templates/sync-catalog")
        assert r.status_code == 200
        data = r.json()
        assert "created" in data
        assert "catalog_version" in data


class TestGenerateEndpoints:

    @pytest.mark.asyncio
    async def test_post_generate_document_201(self, async_client, db):
        pid, r = await _generate_doc_http(async_client, db)
        assert r.status_code == 201
        data = r.json()
        assert data["template_codigo"] == "E-100"
        assert data["docx_path"] is not None

    @pytest.mark.asyncio
    async def test_post_generate_unknown_template_404(self, async_client, db):
        _, pid = await setup_test_project(db)
        await _sync_catalog_http(async_client)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/documents/generate",
            json={"template_codigo": "FAKE-999", "context": {}, "generate_pdf": False, "sign": False},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_post_preview_render_200(self, async_client, db):
        _, pid = await setup_test_project(db)
        await _sync_catalog_http(async_client)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/documents/preview",
            json={"template_codigo": "E-100", "context": {"cliente": {"razon_social": "X"}}},
        )
        assert r.status_code == 200


    @pytest.mark.asyncio
    async def test_post_generate_inactive_template_409(self, async_client, db):
        """Inactive template returns 409."""
        _, pid = await setup_test_project(db)
        await _sync_catalog_http(async_client)
        # Deactivate E-126 via direct DB update
        from sqlalchemy import text as sa_text
        async with _admin_setup(db):
            await db.execute(sa_text("UPDATE templates SET is_active = false WHERE codigo = 'E-126'"))
        await db.flush()
        r = await async_client.post(
            f"{BASE}/projects/{pid}/documents/generate",
            json={"template_codigo": "E-126", "context": {}, "generate_pdf": False, "sign": False},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_post_preview_unknown_template_404(self, async_client, db):
        _, pid = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{pid}/documents/preview",
            json={"template_codigo": "FAKE-999", "context": {}},
        )
        assert r.status_code == 404


class TestDocumentCrudEndpoints:

    @pytest.mark.asyncio
    async def test_get_list_documents_empty_200(self, async_client, db):
        _, pid = await setup_test_project(db)
        r = await async_client.get(f"{BASE}/projects/{pid}/documents")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_get_document_not_found_404(self, async_client, db):
        r = await async_client.get(f"{BASE}/documents/{uuid4()}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_204(self, async_client, db):
        pid, gen_r = await _generate_doc_http(async_client, db)
        assert gen_r.status_code == 201
        doc_id = gen_r.json()["document_id"]
        r = await async_client.delete(f"{BASE}/documents/{doc_id}")
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_post_mark_delivered_200(self, async_client, db):
        pid, gen_r = await _generate_doc_http(async_client, db)
        assert gen_r.status_code == 201
        doc_id = gen_r.json()["document_id"]
        r = await async_client.post(f"{BASE}/documents/{doc_id}/mark-delivered")
        assert r.status_code == 200
        assert r.json()["estado"] == "entregado"


class TestDashboardEndpoint:

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_200_no_404(self, async_client, db):
        _, pid = await setup_test_project(db)
        r = await async_client.get(f"{BASE}/projects/{pid}/documents/dashboard")
        assert r.status_code == 200
        assert r.json()["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_e2e_generate_then_list(self, async_client, db):
        """E2E: generate -> list -> document visible."""
        pid, gen_r = await _generate_doc_http(async_client, db)
        assert gen_r.status_code == 201
        r = await async_client.get(f"{BASE}/projects/{pid}/documents")
        assert r.status_code == 200
        assert len(r.json()) >= 1
