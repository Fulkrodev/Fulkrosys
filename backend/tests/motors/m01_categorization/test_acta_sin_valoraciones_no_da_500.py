"""El acta E-012 de un sistema que perdio sus valoraciones responde 409, no 500.

Encontrado el 2026-09-23 barriendo todos los GET de la API con datos reales:
``GET /systems/{id}/acta-e012`` y ``/acta-e012.json`` devolvian 500. El sistema
estaba categorizado, pero sus tipos de informacion y servicios ya no estaban
(la carga funciona en modo reemplazo), y el acta los recalcula: el servicio
levantaba ValueError y nadie lo traducia. Sin valoraciones no hay acta veraz
que emitir; lo correcto es decir que falta y que hacer.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


async def _sistema_categorizado_y_vaciado(async_client, db) -> str:
    _, project_id = await setup_test_project(db)
    sr = await async_client.post(
        f"/api/v1/categorization/projects/{project_id}/systems",
        json={"nombre": "Sistema que pierde sus valoraciones", "descripcion": "barrido"},
    )
    system_id = sr.json()["id"]
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/information-types",
        json={"items": [{
            "nombre": "Expedientes", "valoracion_d": "MEDIO",
            "valoracion_i": "MEDIO", "valoracion_c": "BAJO",
            "valoracion_a": "BAJO", "valoracion_t": "BAJO",
        }]},
    )
    assert r.status_code == 201, r.text
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/categorize",
        json={"aprobado_por": "Marcos Mata"},
    )
    assert r.status_code in (200, 201), r.text
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE information_types SET deleted_at = now() WHERE system_id = :s"),
            {"s": system_id},
        )
    await db.flush()
    return system_id


@pytest.mark.asyncio
@pytest.mark.parametrize("ruta", ["acta-e012", "acta-e012.json"])
async def test_el_acta_sin_valoraciones_explica_que_falta(async_client, db, ruta):
    system_id = await _sistema_categorizado_y_vaciado(async_client, db)
    r = await async_client.get(f"/api/v1/categorization/systems/{system_id}/{ruta}")
    assert r.status_code == 409, r.text
    assert "valorados" in r.json()["detail"]
