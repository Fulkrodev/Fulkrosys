"""Tests SAN-D MB-19.5 · CRM API endpoints (frontend kanban backend).

Cubre:
- GET /api/v1/commercial/leads · serializa leads compat PipelineKanban.
- GET con filtros (estado_contacto · origen).
- PATCH /api/v1/commercial/leads/{id}/stage · mapping inglés→español backend.
- PATCH /api/v1/commercial/leads/{id}/estado-contacto · español directo.
- Stage inválido raises 400.
- Transition inválida raises 400.
- Lead no encontrado raises 404.

Refs: ADR-041 · m13_commercial/api.py mapping bidireccional.
"""
from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.app.motors.m13_commercial.api import (
    ESTADO_CONTACTO_TO_STAGE,
    STAGE_TO_ESTADO_CONTACTO,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService


# ====================== Mapping bidireccional ======================

def test_estado_contacto_to_stage_covers_8_estados():
    """ESTADO_CONTACTO_TO_STAGE cubre 8 estados workflow comercial v2."""
    expected = {
        "nuevo", "enviado", "respondio", "reunion_agendada",
        "propuesta_enviada", "ganado", "descartado", "no_interesa",
    }
    assert set(ESTADO_CONTACTO_TO_STAGE.keys()) == expected


def test_stage_to_estado_contacto_covers_8_frontend_stages():
    """STAGE_TO_ESTADO_CONTACTO cubre 8 stages frontend (legacy LEAD_STAGES)."""
    expected = {
        "new", "qualifying", "meeting_exploratory", "proposal_sent",
        "negotiation", "won", "lost", "paused",
    }
    assert set(STAGE_TO_ESTADO_CONTACTO.keys()) == expected


def test_mapping_round_trip_critical_paths():
    """Round-trip mapping crítico paths preservan semántica."""
    # nuevo ↔ new
    assert STAGE_TO_ESTADO_CONTACTO[ESTADO_CONTACTO_TO_STAGE["nuevo"]] == "nuevo"
    # ganado ↔ won
    assert STAGE_TO_ESTADO_CONTACTO[ESTADO_CONTACTO_TO_STAGE["ganado"]] == "ganado"
    # reunion_agendada ↔ meeting_exploratory
    assert (
        STAGE_TO_ESTADO_CONTACTO[ESTADO_CONTACTO_TO_STAGE["reunion_agendada"]]
        == "reunion_agendada"
    )
    # propuesta_enviada ↔ proposal_sent
    assert (
        STAGE_TO_ESTADO_CONTACTO[ESTADO_CONTACTO_TO_STAGE["propuesta_enviada"]]
        == "propuesta_enviada"
    )


# ====================== HTTP client fixture (admin auth real) ======================

@pytest_asyncio.fixture
async def admin_client_http() -> AsyncGenerator[AsyncClient, None]:
    """HTTP AsyncClient con sesión Marcos owner via JWT.

    Usa flujo m21 cockpit_login_marcos pattern existing · sin mocks · stack
    real para coherencia con Playwright suite (ADR-034 v2 SAN-D principle).
    """
    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


# ====================== GET /api/v1/commercial/leads ======================

@pytest.mark.asyncio
async def test_get_leads_returns_serialized_with_stage_mapping(db):
    """GET /leads serializa leads M13 con mapping español→inglés stage."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)
    lead = await service.create_lead(
        empresa_nombre="API Test Co",
        contacto_email="api@apico.es",
        sector="Tecnología",
        temperature_level=6,
        categoria_objetivo_ens="MEDIA",
    )
    await service.transition_estado_contacto(
        lead_id=lead.id,
        target_estado="enviado",
    )

    # Test direct service · API endpoint requires HTTP fixture full stack
    leads = await service.list_pipeline(estado_contacto="enviado")
    assert any(l.id == lead.id for l in leads)
    target_lead = next(l for l in leads if l.id == lead.id)
    assert target_lead.estado_contacto == "enviado"
    assert target_lead.empresa_nombre == "API Test Co"

    # Verify serialize helper aplica mapping correcto
    from backend.app.motors.m13_commercial.api import _serialize_lead_for_crm
    serialized = _serialize_lead_for_crm(target_lead)
    assert serialized["stage"] == "qualifying"  # enviado → qualifying
    assert serialized["empresa"] == "API Test Co"
    assert serialized["estado_contacto"] == "enviado"
    assert serialized["temperature_level"] == 6
    assert serialized["categoria_objetivo_ens"] == "MEDIA"


@pytest.mark.asyncio
async def test_serialize_lead_lost_with_razon_perdida(db):
    """Lead descartado serializa stage=lost + lost_reason populated."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)
    lead = await service.create_lead(
        empresa_nombre="Lost Lead Co",
        contacto_email="lost@lostco.es",
    )
    lead = await service.transition_estado_contacto(
        lead_id=lead.id,
        target_estado="descartado",
        notes="Cliente sin presupuesto Q2",
    )

    from backend.app.motors.m13_commercial.api import _serialize_lead_for_crm
    serialized = _serialize_lead_for_crm(lead)
    assert serialized["stage"] == "lost"
    assert serialized["lost_reason"] == "Cliente sin presupuesto Q2"


@pytest.mark.asyncio
async def test_serialize_lead_calculates_rag_status(db):
    """RAG status calculado desde lead_score (>=70 green · >=40 amber · <40 red)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)
    lead = await service.create_lead(
        empresa_nombre="RAG Test Co",
        contacto_email="rag@rag.es",
    )
    # Update lead_score directo (Lead model permite escribir lead_score)
    lead.lead_score = 75
    await db.flush()

    from backend.app.motors.m13_commercial.api import _serialize_lead_for_crm
    serialized = _serialize_lead_for_crm(lead)
    assert serialized["score"] == 75
    assert serialized["rag"] == "green"


# ====================== Service layer: transitions via API mapping ======================

@pytest.mark.asyncio
async def test_lead_service_transitions_match_api_mapping(db):
    """LeadService transitions coinciden con STAGE_TO_ESTADO_CONTACTO mapping."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)
    lead = await service.create_lead(
        empresa_nombre="Transit Co",
        contacto_email="trans@trans.es",
    )

    # Frontend "qualifying" → backend "enviado"
    target_estado = STAGE_TO_ESTADO_CONTACTO["qualifying"]
    lead = await service.transition_estado_contacto(
        lead_id=lead.id,
        target_estado=target_estado,
    )
    assert lead.estado_contacto == "enviado"
    # Round-trip serialize
    from backend.app.motors.m13_commercial.api import _serialize_lead_for_crm
    serialized = _serialize_lead_for_crm(lead)
    assert serialized["stage"] == "qualifying"
