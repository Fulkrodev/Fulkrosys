"""Proyecto ligero + lead_id + guard de coherencia (#7.3).

- create_lightweight_project_for_lead: DRAFT/pre_venta, papel_aapp arrastrado,
  links convertido_a_proyecto_id, idempotente.
- create_session acepta lead_id → OnboardingSession.lead_id.
- guard: los proyectos ligeros quedan FUERA del conteo de proyectos activos.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.models.core import Client, Project
from backend.app.models.onboarding import OnboardingSession
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService
from backend.app.motors.m16_onboarding.enums import Role, Sector
from backend.app.motors.m16_onboarding.service import create_session


async def _make_lead(db, *, cif=None, papel="alojamos_tratamos_datos", categoria="MEDIA"):
    cif = cif or f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await LeadService(db).create_lead(
        empresa_nombre="LeadCo SL", contacto_email="lead@co.es",
        empresa_cif=cif, categoria_objetivo_ens=categoria,
    )
    lead.papel_aapp = papel
    lead.archetype_ens = "privado_licita_aapp"
    await db.flush()
    return lead


@pytest.mark.asyncio
async def test_create_lightweight_project_draft_pre_venta(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead = await _make_lead(db)
    project = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)

    assert project.lifecycle_state == "DRAFT"
    assert project.fase == "pre_venta"
    assert project.categoria_objetivo == "MEDIA"
    assert project.papel_aapp == "alojamos_tratamos_datos"   # arrastrado del lead
    assert lead.convertido_a_proyecto_id == project.id        # mismo proyecto que evolucionará


@pytest.mark.asyncio
async def test_create_lightweight_project_idempotent(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead = await _make_lead(db)
    svc = CommercialWorkflowService(db)
    p1 = await svc.create_lightweight_project_for_lead(lead)
    p2 = await svc.create_lightweight_project_for_lead(lead)
    assert p1.id == p2.id   # NO crea un segundo proyecto del mismo lead


@pytest.mark.asyncio
async def test_create_session_sets_lead_id(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead = await _make_lead(db)
    project = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)

    result = await create_session(
        db=db, project_id=project.id, sector=Sector.PRECLIENTE, role=Role.SPONSOR,
        interlocutor_email="lead@co.es", interlocutor_name="Ana",
        ttl_hours=336, language="es", metadata_extra=None,
        purpose=None, lead_id=lead.id,
    )
    onb = await db.get(OnboardingSession, result["session_id"])
    assert onb is not None
    assert onb.lead_id == lead.id   # traza lead↔onboarding formalizada


@pytest.mark.asyncio
async def test_guard_lightweight_excluded_from_active_projects(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead = await _make_lead(db)
    light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)

    # Proyecto real (no ligero).
    c = Client(nombre="RealCo", cif=f"B{uuid.uuid4().hex[:8].upper()}")
    db.add(c)
    await db.flush()
    real = Project(client_id=c.id, nombre="RealCo ENS", lifecycle_state="SIGNED", fase="onboarding")
    db.add(real)
    await db.flush()

    guard = "NOT (lifecycle_state = 'DRAFT' AND fase = 'pre_venta')"
    light_counted = await db.scalar(
        text(f"SELECT count(*) FROM projects WHERE id = :id AND {guard}"),
        {"id": str(light.id)},
    )
    real_counted = await db.scalar(
        text(f"SELECT count(*) FROM projects WHERE id = :id AND {guard}"),
        {"id": str(real.id)},
    )
    assert light_counted == 0   # ligero EXCLUIDO del conteo de activos
    assert real_counted == 1    # real SÍ cuenta
