"""#7.4 · Promoción del proyecto ligero en la firma (dos ramas).

- Rama A: lead con proyecto LIGERO → la firma PROMUEVE el mismo (no duplica).
- Rama B: lead sin proyecto ligero → la firma CREA vía path común.
- Nadie firma sin proyecto.
- Idempotencia: re-firma de un proyecto ya promovido → already_converted.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.models.core import Project
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)
from backend.tests.motors.m13_commercial.test_commercial_workflow_service import (
    _setup_lead_and_contract,
)


async def _count_projects_for_client(db, client_id) -> int:
    return await db.scalar(
        select(func.count()).select_from(Project).where(Project.client_id == client_id)
    )


@pytest.mark.asyncio
async def test_signing_promotes_lightweight_no_duplicate(db):
    """Rama A · con proyecto ligero, la firma promueve el MISMO proyecto."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    lead.papel_aapp = "alojamos_tratamos_datos"
    await db.flush()

    workflow = CommercialWorkflowService(db)
    light = await workflow.create_lightweight_project_for_lead(lead)
    assert light.lifecycle_state == "DRAFT"
    assert light.fase == "pre_venta"
    client_id = light.client_id

    result = await workflow.handle_contract_signed(contract_id)

    assert result["status"] == "converted"
    assert result["project_id"] == str(light.id)            # MISMO proyecto
    assert str(lead.convertido_a_proyecto_id) == str(light.id)

    await db.refresh(light)
    assert light.lifecycle_state == "SIGNED"                 # promovido
    assert light.fase == "onboarding"                        # ya NO es ligero
    assert light.papel_aapp == "alojamos_tratamos_datos"     # arrastrado del lead

    # NO duplica: un solo proyecto para el cliente.
    assert await _count_projects_for_client(db, client_id) == 1


@pytest.mark.asyncio
async def test_signing_creates_when_no_lightweight(db):
    """Rama B · sin proyecto ligero, la firma crea vía path común."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    lead.papel_aapp = "presta_servicio_aapp"
    await db.flush()
    assert lead.convertido_a_proyecto_id is None  # sin ligero

    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)

    assert result["status"] == "converted"
    project = await db.get(Project, uuid.UUID(result["project_id"]))
    assert project is not None
    assert project.lifecycle_state == "SIGNED"
    assert project.papel_aapp == "presta_servicio_aapp"      # arrastrado rama B
    await db.refresh(lead)
    assert str(lead.convertido_a_proyecto_id) == result["project_id"]


@pytest.mark.asyncio
async def test_nobody_signs_without_project(db):
    """Ambas ramas dejan SIEMPRE un proyecto enlazado al lead."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    await CommercialWorkflowService(db).handle_contract_signed(contract_id)
    await db.refresh(lead)
    assert lead.convertido_a_proyecto_id is not None
    assert await db.get(Project, lead.convertido_a_proyecto_id) is not None


@pytest.mark.asyncio
async def test_signing_idempotent_after_promotion(db):
    """Re-firma de un proyecto YA promovido → already_converted (no duplica)."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    workflow = CommercialWorkflowService(db)
    light = await workflow.create_lightweight_project_for_lead(lead)
    client_id = light.client_id

    r1 = await workflow.handle_contract_signed(contract_id)
    assert r1["status"] == "converted"
    r2 = await workflow.handle_contract_signed(contract_id)
    assert r2["status"] == "already_converted"
    assert r2["project_id"] == str(light.id)

    assert await _count_projects_for_client(db, client_id) == 1
