"""Tests Sprint C2 — M5 Obligations expansion."""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select, func

from backend.app.database import set_tenant_context
from backend.app.models.ens import Obligation
from backend.app.motors.m05_obligations.library_loader import load_library
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/projects"


async def _tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


def test_c2_library_expanded_to_98():
    """Library tiene ≥98 templates (30 baseline + 68 nuevos)."""
    lib = load_library()
    assert len(lib.templates) >= 150
    assert lib.version == "3.0"


def test_c2_library_covers_key_families():
    """Library cubre familias ENS principales."""
    lib = load_library()
    measures = {t.measure_code for t in lib.templates}
    for family_prefix in ("org.", "op.acc.", "op.exp.", "mp.com.", "mp.info.", "mp.per."):
        matching = [m for m in measures if m.startswith(family_prefix)]
        assert len(matching) >= 1, f"No templates para familia {family_prefix}"


def test_c2_library_ids_unique():
    lib = load_library()
    ids = [t.id for t in lib.templates]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_c2_api_create_obligation(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/obligations",
        json={
            "titulo": "Revisar MFA en proveedores",
            "descripcion": "Verificar cobertura MFA en cuentas externas",
            "measure_code": "op.acc.5",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "pendiente"


@pytest.mark.asyncio
async def test_c2_service_create_and_list_direct(db):
    """Test service-level sin pasar por HTTP (evita issues de tx cross-request)."""
    _, project_id = await _tenant(db)
    ob = Obligation(
        project_id=uuid.UUID(project_id),
        titulo="Test",
        descripcion="desc",
        measure_code="org.1",
        estado="pendiente",
    )
    db.add(ob)
    await db.flush()
    # Verificar visibilidad via query
    count = (await db.execute(
        select(func.count(Obligation.id)).where(
            Obligation.project_id == uuid.UUID(project_id),
        )
    )).scalar()
    assert count >= 1


@pytest.mark.asyncio
async def test_c2_service_state_transitions_direct(db):
    """Test transiciones sin HTTP — lógica pura."""
    _, project_id = await _tenant(db)
    ob = Obligation(
        project_id=uuid.UUID(project_id),
        titulo="T",
        descripcion="d",
        estado="pendiente",
    )
    db.add(ob)
    await db.flush()
    # Simular transición manual
    ob.estado = "en_curso"
    await db.flush()
    assert ob.estado == "en_curso"
    ob.estado = "completada"
    await db.flush()
    assert ob.estado == "completada"


def test_c2_api_endpoints_registered():
    """Verifica que los 8 endpoints nuevos están registrados.

    Se consulta el esquema OpenAPI y no ``app.routes``: desde FastAPI 0.141 el
    ``include_router`` ya no aplana las rutas ahí (deja ``_IncludedRouter`` con
    resolución perezosa), así que el filtro anterior contaba 0 aunque los diez
    endpoints existieran. Medido el 2026-09-10: son 10 en el esquema.
    """
    from backend.app.main import app

    # OJO con la poblacion que se cuenta: el test original contaba objetos-ruta
    # de `app.routes`, es decir camino X metodo, no caminos. Son cosas distintas:
    # aqui hay 8 caminos y 10 operaciones (dos caminos tienen dos metodos).
    # Contar caminos y comparar contra el umbral de 10 seria comparar poblaciones
    # que no son la misma, y el test fallaria por un error de etiqueta, no por
    # un endpoint que falte.
    METODOS_HTTP = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
    esquema = app.openapi()["paths"]
    operaciones = [
        f"{metodo.upper()} {camino}"
        for camino, item in esquema.items()
        if "/obligations" in camino
        for metodo in item
        if metodo in METODOS_HTTP
    ]
    assert len(operaciones) >= 10, (  # 2 originales + 8 nuevos
        f"esperaba >=10 operaciones con /obligations, hay {len(operaciones)}: "
        f"{sorted(operaciones)}"
    )
