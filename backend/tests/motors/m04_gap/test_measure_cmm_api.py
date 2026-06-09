"""#21 cierre Ola 4 · ASGI in-process del endpoint CMM por medida (sin uvicorn).

Verifica la 3ª lente (madurez CMM) de la fila SoA vía el endpoint REAL por HTTP
(ASGITransport · misma sesión RLS que el test · contra fulkro_test):
- implantada → L3 (Definido · sin evidencia → no L4)
- implantada + evidencia VERDE → L4 (acople #20→#21)
- no_aplica → cmm_level None (excluida de la madurez)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.motors.m04_gap.test_service import _setup_with_dda

BASE_ADMIN = "/api/v1/admin/projects"


async def _first_applicable(db, pid):
    row = (await db.execute(text(
        "SELECT de.id, em.codigo FROM dda_entries de "
        "JOIN ens_measures em ON em.id = de.measure_id "
        "WHERE de.project_id = :pid AND de.aplicabilidad != 'no_aplica' "
        "AND de.deleted_at IS NULL ORDER BY em.codigo LIMIT 1"
    ), {"pid": str(pid)})).first()
    return str(row[0]), row[1]


async def _set_estado(db, dda_entry_id, estado):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(text(
        "UPDATE dda_entries SET estado_implementacion = :e WHERE id = :id"
    ), {"e": estado, "id": dda_entry_id})
    await db.execute(text("RESET ROLE"))
    await db.flush()


@pytest.mark.asyncio
async def test_admin_cmm_endpoint_implantada_L3(async_client, db):
    """implantada → CMM L3 (Definido) · sin evidencia no llega a L4."""
    svc, pid = await _setup_with_dda(db, "MEDIA")
    dda_entry_id, codigo = await _first_applicable(db, pid)
    await _set_estado(db, dda_entry_id, "implantada")
    await db.execute(text("RESET ROLE"))

    r = await async_client.get(
        f"{BASE_ADMIN}/{pid}/controls/cmm?measure_code={codigo}",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["measure_code"] == codigo
    assert body["estado_implementacion"] == "implantada"
    assert body["cmm_level"] == "L3"
    assert body["cmm_label"] == "Definido"
    assert body["target_level"] == "L3"  # MEDIA


@pytest.mark.asyncio
async def test_admin_cmm_endpoint_implantada_plus_verde_L4(async_client, db):
    """implantada + evidencia VERDE (vigente·clean·no caducada) → L4 (acople #20→#21)."""
    svc, pid = await _setup_with_dda(db, "ALTA")
    dda_entry_id, codigo = await _first_applicable(db, pid)
    await _set_estado(db, dda_entry_id, "implantada")

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(text(
        "INSERT INTO evidence (id, project_id, measure_code, vigente, scan_status, "
        "fecha_caducidad, created_at) VALUES (:id, :pid, :cod, TRUE, 'clean', "
        "(now() + interval '365 days')::date, now())"
    ), {"id": str(uuid.uuid4()), "pid": str(pid), "cod": codigo})
    await db.execute(text("RESET ROLE"))
    await db.flush()

    r = await async_client.get(
        f"{BASE_ADMIN}/{pid}/controls/cmm?measure_code={codigo}",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cmm_level"] == "L4", "implantada + evidencia verde → L4"
    assert body["cmm_label"] == "Gestionado"
    assert body["target_level"] == "L4"  # ALTA


@pytest.mark.asyncio
async def test_admin_cmm_endpoint_no_aplica_excluida(async_client, db):
    """estado_implementacion = no_aplica → cmm_level None (excluida de la madurez)."""
    svc, pid = await _setup_with_dda(db, "BASICA")
    dda_entry_id, codigo = await _first_applicable(db, pid)
    await _set_estado(db, dda_entry_id, "no_aplica")
    await db.execute(text("RESET ROLE"))

    r = await async_client.get(
        f"{BASE_ADMIN}/{pid}/controls/cmm?measure_code={codigo}",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["estado_implementacion"] == "no_aplica"
    assert body["cmm_level"] is None
    assert body["cmm_label"] is None
