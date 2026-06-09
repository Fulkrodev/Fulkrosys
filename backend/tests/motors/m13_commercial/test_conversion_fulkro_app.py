"""#7.6 · verificación anti-falso-verde + audit_log R6 de la conversión.

Los tests de #7.4 corren con ``SET LOCAL ROLE fulkro_app_bypassrls`` (superusuario · RLS
bypass). En producción ``confirm_signing`` (cliente · magic-link) NO fija
contexto de tenant y corre como ``fulkro_app`` (RLS estricta). Estos tests
ejercitan la conversión BAJO fulkro_app para cazar el falso-verde.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.models.core import Project
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)
from backend.tests.motors.m13_commercial.test_commercial_workflow_service import (
    _setup_lead_and_contract,
)


async def _as_fulkro_app_no_context(db):
    """Simula producción: fulkro_app (RLS estricta) SIN contexto de tenant."""
    await db.execute(text("RESET ROLE"))
    await db.execute(text("SELECT set_config('app.current_client_id', '', true)"))
    await db.execute(text("SELECT set_config('app.current_project_id', '', true)"))


@pytest.mark.asyncio
async def test_handle_contract_signed_promotes_under_fulkro_app(db):
    """Bajo fulkro_app (como confirm_signing en prod) la firma PROMUEVE el
    proyecto ligero · no falla la RLS ni crea un duplicado."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)  # rol = fulkro aquí
    lead.papel_aapp = "alojamos_tratamos_datos"
    await db.flush()
    light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)
    light_id = light.id
    client_id = light.client_id

    await _as_fulkro_app_no_context(db)

    result = await CommercialWorkflowService(db).handle_contract_signed(contract_id)

    assert result["status"] == "converted"
    assert result["project_id"] == str(light_id)  # promovido, NO duplicado

    # NO duplica + audit_log R6 de la conversión (verificación bypass RLS).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    n = await db.scalar(text(
        "SELECT count(*) FROM projects WHERE client_id = :cid"
    ), {"cid": str(client_id)})
    assert n == 1
    audit = await db.scalar(text(
        "SELECT count(*) FROM audit_log WHERE accion = 'lead.converted_to_project' "
        "AND project_id = :pid"
    ), {"pid": str(light_id)})
    assert audit == 1  # R6 hash chain · trigger


@pytest.mark.asyncio
async def test_handle_contract_signed_idempotent_under_fulkro_app(db):
    """Re-firma bajo fulkro_app → already_converted SIN duplicar. Regresión del
    bug de idempotencia: leer el proyecto bajo el dueño autoritativo (no el
    client re-resuelto) · la RLS no debe ocultar el proyecto real."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)
    light_id = light.id
    client_id = light.client_id

    await _as_fulkro_app_no_context(db)
    r1 = await CommercialWorkflowService(db).handle_contract_signed(contract_id)
    assert r1["status"] == "converted"
    assert r1["project_id"] == str(light_id)

    # Re-firma como fulkro_app (el contrato ya tiene project_id → la RLS de
    # contracts requiere el contexto del proyecto, que la firma real conserva).
    # El proyecto ya es REAL (promovido) → idempotente, no duplica.
    r2 = await CommercialWorkflowService(db).handle_contract_signed(contract_id)
    assert r2["status"] == "already_converted"
    assert r2["project_id"] == str(light_id)

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    n = await db.scalar(text(
        "SELECT count(*) FROM projects WHERE client_id = :cid"
    ), {"cid": str(client_id)})
    assert n == 1  # la re-firma NO duplica


@pytest.mark.asyncio
async def test_handle_contract_signed_creates_under_fulkro_app(db):
    """Bajo fulkro_app la firma SIN proyecto ligero crea el proyecto (la RLS
    no bloquea el INSERT · contexto fijado por el propio servicio)."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    await _as_fulkro_app_no_context(db)

    result = await CommercialWorkflowService(db).handle_contract_signed(contract_id)

    assert result["status"] == "converted"
    assert result["project_id"] is not None
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    proj = await db.get(Project, uuid.UUID(result["project_id"]))
    assert proj is not None
    assert proj.lifecycle_state == "SIGNED"
    audit = await db.scalar(text(
        "SELECT count(*) FROM audit_log WHERE accion = 'lead.converted_to_project' "
        "AND project_id = :pid"
    ), {"pid": result["project_id"]})
    assert audit == 1  # R6 hash chain · conversión rama fresca
