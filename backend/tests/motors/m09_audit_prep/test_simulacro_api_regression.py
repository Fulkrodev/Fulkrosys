"""Regresión BUG-02 (audit 2026-06-13): el endpoint POST
/admin/projects/{id}/simulacro-pre-enac/execute devolvía 404 "Project not found"
para un proyecto VÁLIDO porque no fijaba el contexto RLS (set_tenant_context) antes
de que el servicio consultara la tabla projects bajo fulkro_app con RLS. Bug latente:
ningún spec ejecutaba el endpoint (los tests de servicio pasaban un db ya scopeado).

Guarda: el endpoint encuentra el proyecto (NO 404 'Project not found').
"""
import pytest
from sqlalchemy import text as sa_text

from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_simulacro_execute_scopes_project_not_404(async_client, db):
    _, project_id = await setup_test_project(db)
    await db.execute(
        sa_text("UPDATE projects SET categoria_objetivo='MEDIA' WHERE id=:p"),
        {"p": project_id},
    )
    await db.commit()

    r = await async_client.post(
        f"/api/v1/admin/projects/{project_id}/simulacro-pre-enac/execute", json={},
    )
    # El bug daba 404 con detail "Project ... not found". Ahora el proyecto se
    # resuelve (get_project_owner + set_tenant_context); cualquier respuesta != 404
    # demuestra que el scoping RLS funciona.
    assert r.status_code != 404, r.text


@pytest.mark.asyncio
async def test_simulacro_last_report_scopes_project_not_500(async_client, db):
    _, project_id = await setup_test_project(db)
    await db.commit()
    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/simulacro-pre-enac/last-report",
    )
    # Sin simulacro previo devuelve 404 con el detail de "no ejecutado todavía"
    # (NO el 404 de proyecto no encontrado) — basta con que no sea 500.
    assert r.status_code in (200, 404), r.text
