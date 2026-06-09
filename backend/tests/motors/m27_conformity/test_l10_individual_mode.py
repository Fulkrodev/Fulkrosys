"""L-10 (FRENTE L) · conformity route marca individual_mode + acumulación de
roles (RSeg=RSis) para perfil autónomo/micro · NO cambia route_type."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.database import set_tenant_context
from backend.app.motors.m27_conformity.conformity_service_paso5 import (
    ConformityServicePaso5,
)
from backend.tests.conftest import _admin_setup, setup_test_project

pytestmark = pytest.mark.asyncio


async def _project(db, *, categoria: str, tamano: str | None) -> uuid.UUID:
    cid, pid = await setup_test_project(db)
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = :c, tamano_empleados = :t "
            "WHERE id = :pid"
        ), {"c": categoria, "t": tamano, "pid": pid})
    await set_tenant_context(db, client_id=uuid.UUID(cid), project_id=uuid.UUID(pid))
    return uuid.UUID(pid)


async def test_l10_micro_basica_sets_individual_mode(db):
    pid = await _project(db, categoria="BASICA", tamano="micro")
    route = await ConformityServicePaso5().initialize_conformity_route(db, pid)
    assert route.route_type == "declaracion_basica"  # NO cambia
    assert route.metadata_jsonb.get("individual_mode") is True
    assert route.metadata_jsonb.get("rseg_rsys_same_person") is True


async def test_l10_non_micro_no_individual_mode(db):
    pid = await _project(db, categoria="MEDIA", tamano="mediano")
    route = await ConformityServicePaso5().initialize_conformity_route(db, pid)
    assert route.route_type == "certificacion_enac"
    assert "individual_mode" not in route.metadata_jsonb
