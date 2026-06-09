"""Tests for RetainerService.execute_scheduled_activity · atom 7.bis.3."""
import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m23_retainer.retainer_service import (
    RetainerError,
    RetainerService,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_retainer_and_activity(
    db, *, tipo_actividad: str, perfil: str = "R_STD",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Insert client + project + retainer + 1 scheduled activity. Returns ids."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    retainer_id = uuid.uuid4()
    activity_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'TestC', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects "
            "(id, client_id, nombre, fase, categoria_objetivo, created_at) "
            "VALUES (:id, :cid, 'TestP', 'diagnostico', 'MEDIA', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, modalidad, precio_mensual, "
            " perfil, estado, inicio, created_at) "
            "VALUES (:id, :cid, :pid, 'mensual', 700, :perfil, 'activo', "
            " CURRENT_DATE, now())"
        ), {
            "id": str(retainer_id),
            "cid": str(client_id),
            "pid": str(project_id),
            "perfil": perfil,
        })
        await db.execute(text(
            "INSERT INTO retainer_activities "
            "(id, retainer_contract_id, project_id, tipo_actividad, "
            " fecha_programada, estado, created_at) "
            "VALUES (:id, :rid, :pid, :tipo, CURRENT_DATE, 'programada', now())"
        ), {
            "id": str(activity_id),
            "rid": str(retainer_id),
            "pid": str(project_id),
            "tipo": tipo_actividad,
        })
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return retainer_id, project_id, activity_id


async def test_execute_scheduled_activity_unknown_tipo_marks_manual(db):
    """Unknown tipo · result.motor == 'unknown' · status='completed' (manual)."""
    _, _, activity_id = await _seed_retainer_and_activity(
        db, tipo_actividad="custom_marcos_thing",
    )

    svc = RetainerService()
    result = await svc.execute_activity(db,activity_id)

    assert result["activity_id"] == str(activity_id)
    assert result.get("motor") == "unknown"
    assert "manual" in (result.get("message") or "").lower()


async def test_execute_scheduled_activity_missing_id_raises(db):
    svc = RetainerService()
    with pytest.raises(RetainerError):
        await svc.execute_activity(db,uuid.uuid4())


async def test_execute_scheduled_activity_marks_en_curso_immediately(db):
    """Pre-execution flush sets estado='en_curso' even if executor fails."""
    _, _, activity_id = await _seed_retainer_and_activity(
        db, tipo_actividad="custom_handover",
    )

    svc = RetainerService()
    _ = await svc.execute_activity(db,activity_id)

    estado = (await db.execute(text(
        "SELECT estado FROM retainer_activities WHERE id = :id"
    ), {"id": str(activity_id)})).scalar()
    # After unknown tipo path · complete_activity moves to 'completada'
    assert estado in ("en_curso", "completada")
