"""Tests for DriftComputeService · MB-7.bis atom 7.bis.2."""
import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m23_retainer.drift_compute_service import (
    DriftComputeService,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _setup_retainer(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    retainer_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'C1', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'P1', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, modalidad, precio_mensual, perfil, "
            " estado, inicio, created_at) "
            "VALUES (:id, :cid, :pid, 'mensual', 700, 'R_STD', 'activo', "
            " CURRENT_DATE, now())"
        ), {
            "id": str(retainer_id),
            "cid": str(client_id),
            "pid": str(project_id),
        })
        # Seed an expired evidence to trigger evidencias dim
        await db.execute(text(
            "INSERT INTO evidence "
            "(id, project_id, tipo, fecha_caducidad, vigente, created_at) "
            "VALUES (:id, :pid, 'documento', "
            "  NOW() - INTERVAL '30 days', false, now())"
        ), {"id": str(uuid.uuid4()), "pid": str(project_id)})
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return client_id, project_id, retainer_id


async def test_compute_drift_runs_10_dims(db):
    _, _, retainer_id = await _setup_retainer(db)

    svc = DriftComputeService()
    result = await svc.compute_drift_for_retainer(db, retainer_id)

    assert result.dims_computed == 10
    dims = {r.dimension for r in result.results}
    assert dims == {
        "evidencias", "normativa", "identidad", "contratos",
        "proveedores", "roles", "infraestructura", "overlay",
        "cpstic", "continuidad",
    }


async def test_compute_drift_registers_evidence_dim_when_expired(db):
    """Expired evidence row should trigger evidencias drift event."""
    _, project_id, retainer_id = await _setup_retainer(db)

    svc = DriftComputeService()
    result = await svc.compute_drift_for_retainer(db, retainer_id)

    assert result.drifts_registered >= 1
    events = (await db.execute(text(
        "SELECT dimension, severidad FROM retainer_drift_events "
        "WHERE retainer_contract_id = :rid"
    ), {"rid": str(retainer_id)})).mappings().all()
    dims = {e["dimension"] for e in events}
    assert "evidencias" in dims


async def test_compute_drift_does_not_register_when_no_delta(db):
    """A retainer with no expired evidence / no recent changes should
    register fewer drifts (proveedores/infraestructura/overlay always
    LOW + no delta)."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    retainer_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'CleanC', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'CleanP', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, modalidad, precio_mensual, perfil, "
            " estado, inicio, created_at) "
            "VALUES (:id, :cid, :pid, 'mensual', 300, 'R_LITE', 'activo', "
            " CURRENT_DATE, now())"
        ), {
            "id": str(retainer_id),
            "cid": str(client_id),
            "pid": str(project_id),
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

    svc = DriftComputeService()
    result = await svc.compute_drift_for_retainer(db, retainer_id)
    assert result.dims_computed == 10
    # Clean project should have 0 drift events registered
    assert result.drifts_registered == 0
