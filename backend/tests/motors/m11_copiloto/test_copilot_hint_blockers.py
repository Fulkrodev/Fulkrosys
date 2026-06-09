"""Frente 3 · FASE 2 · el hint admin /copilot/hint expone state.blockers.

Verifica la EXPOSICIÓN (no recalcula nada · la lógica vive en _detect_blockers):
cuando hay separación de roles no conforme (MEDIA + RSEG/RSIS misma persona) el
hint devuelve un blocker m30 (waiting_on=admin); sin conflicto, no aparece.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.core.workflow_phase import WorkflowPhase
from backend.tests.conftest import _admin_setup, setup_test_project
from backend.tests.motors.m11_copiloto.test_workflow_state_scanner import (
    _set_project_categoria,
    _set_project_phase,
)

HINT = "/api/v1/copilot/hint?project_id={pid}"


async def _seed_rseg_rsis_same_person(db, client_id_str):
    """2 contactos m30 con el MISMO full_name (emails distintos · UNIQUE) en
    RSEG y RSIS → violación CCN-STIC-801 (separación de roles no conforme)."""
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO client_contacts (id, client_id, full_name, email, "
            " role_title, role_category, is_active, created_at, updated_at) VALUES "
            "(gen_random_uuid(), :cid, 'Juan Perez', 'jp-seg@example.com', "
            " 'Responsable Seguridad', 'responsable_seguridad', true, now(), now()), "
            "(gen_random_uuid(), :cid, 'Juan Perez', 'jp-sis@example.com', "
            " 'Responsable Sistema', 'responsable_sistema', true, now(), now())"
        ), {"cid": client_id_str})


@pytest.mark.asyncio
async def test_admin_hint_exposes_governance_blocker(async_client, db):
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_categoria(db, project_uuid, "MEDIA")
    await _set_project_phase(db, project_uuid, WorkflowPhase.ADECUACION)
    await _seed_rseg_rsis_same_person(db, client_id_str)

    r = await async_client.get(HINT.format(pid=project_id_str))
    assert r.status_code == 200, r.text
    blockers = r.json()["blockers"]
    m30 = [b for b in blockers if b["motor"] == "m30"]
    assert len(m30) == 1, f"esperaba blocker m30 · blockers={blockers}"
    assert m30[0]["waiting_on"] == "admin"
    assert "RSeg" in m30[0]["description"] or "Separación" in m30[0]["description"]


@pytest.mark.asyncio
async def test_admin_hint_no_m30_blocker_when_no_conflict(async_client, db):
    _client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _set_project_categoria(db, project_uuid, "MEDIA")
    await _set_project_phase(db, project_uuid, WorkflowPhase.ADECUACION)
    # sin contactos en conflicto → sin violación de separación.

    r = await async_client.get(HINT.format(pid=project_id_str))
    assert r.status_code == 200, r.text
    blockers = r.json()["blockers"]
    assert all(b["motor"] != "m30" for b in blockers), f"blockers={blockers}"
