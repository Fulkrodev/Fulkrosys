"""Tests R05 · E-155 Documento de Alcance del SGSI · scope estructurado.

Cubre:
- ``build_e155_alcance_context``: servicios (tipo finalista/instrumental), sedes
  (tipo física/cloud + país), exclusiones, dimensiones DICAT reales (regla del
  máximo) y gate ``E155ScopeEmptyError``.
- CRUD de scope (m01): load_services con tipo, sites, exclusions, PATCH tipo.
- Endpoint ``POST /alcance-sgsi/generate`` → 409 si no hay alcance.
"""
import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m06_document_factory.alcance_generator import (
    E155ScopeEmptyError,
    build_e155_alcance_context,
)
from backend.tests.conftest import setup_test_project


async def _set_ctx(db, client_id, project_id):
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )


async def _seed_system(async_client, project_id, nombre="Sistema Alcance"):
    resp = await async_client.post(
        f"/api/v1/categorization/projects/{project_id}/systems",
        json={"nombre": nombre, "frontera": "App web + BBDD + pasarela"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ================================================================
# CRUD scope (m01) · sedes + exclusiones + tipo de servicio
# ================================================================

class TestScopeCrud:
    @pytest.mark.asyncio
    async def test_sites_crud_roundtrip(self, async_client, db):
        _, project_id = await setup_test_project(db)
        system_id = await _seed_system(async_client, project_id)

        resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/sites",
            json={"items": [
                {"nombre": "Sede central", "tipo": "sede_fisica",
                 "direccion": "Calle Mayor 1", "pais": "España"},
                {"nombre": "AWS eu-west-1", "tipo": "region_cloud", "pais": "Irlanda"},
            ]},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert len(data) == 2
        assert {d["tipo"] for d in data} == {"sede_fisica", "region_cloud"}

        getr = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/sites"
        )
        assert getr.status_code == 200
        assert len(getr.json()) == 2

    @pytest.mark.asyncio
    async def test_sites_invalid_tipo_422(self, async_client, db):
        _, project_id = await setup_test_project(db)
        system_id = await _seed_system(async_client, project_id)
        resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/sites",
            json={"items": [{"nombre": "X", "tipo": "no_valido"}]},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_exclusions_crud_roundtrip(self, async_client, db):
        _, project_id = await setup_test_project(db)
        system_id = await _seed_system(async_client, project_id)
        resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/exclusions",
            json={"items": [
                {"elemento": "Web informativa",
                 "justificacion": "No presta servicio a la AAPP"},
            ]},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()[0]["elemento"] == "Web informativa"
        getr = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/exclusions"
        )
        assert len(getr.json()) == 1

    @pytest.mark.asyncio
    async def test_service_tipo_patch(self, async_client, db):
        _, project_id = await setup_test_project(db)
        system_id = await _seed_system(async_client, project_id)
        svc_resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [{"nombre": "Sede electrónica", "tipo": "finalista"}]},
        )
        assert svc_resp.status_code == 201, svc_resp.text
        svc = svc_resp.json()[0]
        assert svc["tipo"] == "finalista"

        patch = await async_client.patch(
            f"/api/v1/categorization/systems/{system_id}/services/{svc['id']}/tipo",
            json={"tipo": "instrumental"},
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["tipo"] == "instrumental"


# ================================================================
# Builder build_e155_alcance_context
# ================================================================

class TestBuildE155Context:
    @pytest.mark.asyncio
    async def test_full_scope_context(self, async_client, db):
        client_id, project_id = await setup_test_project(db)
        system_id = await _seed_system(async_client, project_id, "Plataforma Tramitación")
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Expedientes", "valoracion_i": "ALTO", "valoracion_c": "MEDIO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "Sede electrónica", "tipo": "finalista", "valoracion_d": "MEDIO"},
                {"nombre": "Directorio", "tipo": "instrumental"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/sites",
            json={"items": [
                {"nombre": "AWS eu-west-1", "tipo": "region_cloud", "pais": "Irlanda"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/exclusions",
            json={"items": [{"elemento": "Web informativa", "justificacion": "Fuera AAPP"}]},
        )

        await _set_ctx(db, client_id, project_id)
        ctx = await build_e155_alcance_context(db, uuid.UUID(project_id))

        servicios = ctx["alcance"]["servicios"]
        assert {s["nombre"]: s["tipo"] for s in servicios} == {
            "Sede electrónica": "finalista", "Directorio": "instrumental",
        }
        sedes = ctx["alcance"]["sedes"]
        assert sedes[0]["tipo"] == "region_cloud"
        assert sedes[0]["pais"] == "Irlanda"
        assert ctx["alcance"]["exclusiones"][0]["elemento"] == "Web informativa"
        # regla del máximo: info_type integridad=ALTO domina → dim integridad ALTO
        assert ctx["categorizacion"]["dimensiones"]["integridad"] == "ALTO"
        assert ctx["categorizacion"]["nivel_global"] == "ALTA"
        assert ctx["proyecto"]["servicio_principal"] == "Sede electrónica"  # finalista
        assert ctx["sistema"]["nombre"] == "Plataforma Tramitación"

    @pytest.mark.asyncio
    async def test_gate_no_system(self, db):
        client_id, project_id = await setup_test_project(db)
        await _set_ctx(db, client_id, project_id)
        with pytest.raises(E155ScopeEmptyError):
            await build_e155_alcance_context(db, uuid.UUID(project_id))

    @pytest.mark.asyncio
    async def test_gate_system_without_scope(self, async_client, db):
        client_id, project_id = await setup_test_project(db)
        await _seed_system(async_client, project_id)
        await _set_ctx(db, client_id, project_id)
        with pytest.raises(E155ScopeEmptyError):
            await build_e155_alcance_context(db, uuid.UUID(project_id))


# ================================================================
# Endpoint generate · gate 409
# ================================================================

class TestGenerateEndpointGate:
    @pytest.mark.asyncio
    async def test_generate_409_when_scope_empty(self, async_client, db):
        _, project_id = await setup_test_project(db)
        # sin sistema → builder lanza E155ScopeEmptyError → 409
        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/alcance-sgsi/generate",
        )
        assert resp.status_code == 409, resp.text
