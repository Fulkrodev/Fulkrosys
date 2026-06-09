"""Tests SAN-D MB-19.2 · LeadService.

Cubre:
- create_lead idempotent (dedup por email + origen).
- transition_estado_contacto valid + invalid + side effects.
- list_pipeline filters.

Refs: ADR-041 · LeadService.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.models.commercial import LeadStageHistory
from backend.app.motors.m13_commercial.services.lead_service import (
    LeadService,
    InvalidTransitionError,
    LeadNotFoundError,
    LeadServiceError,
    VALID_TRANSITIONS,
)
from backend.tests.conftest import _admin_setup


# ====================== VALID_TRANSITIONS structure ======================

def test_valid_transitions_covers_8_estados():
    """8 estados workflow comercial v2 definidos."""
    expected_estados = {
        "nuevo", "enviado", "respondio", "reunion_agendada",
        "propuesta_enviada", "ganado", "descartado", "no_interesa",
    }
    assert set(VALID_TRANSITIONS.keys()) == expected_estados


def test_valid_transitions_ganado_terminal():
    """Estado 'ganado' es terminal (no transitions out)."""
    assert VALID_TRANSITIONS["ganado"] == frozenset()


def test_valid_transitions_nuevo_progression():
    """Estado 'nuevo' permite transición a enviado/descartado/no_interesa."""
    assert "enviado" in VALID_TRANSITIONS["nuevo"]
    assert "descartado" in VALID_TRANSITIONS["nuevo"]
    assert "no_interesa" in VALID_TRANSITIONS["nuevo"]


# ====================== create_lead ======================

@pytest.mark.asyncio
async def test_create_lead_basic(db):
    """create_lead crea Lead + audit trail row."""
    async with _admin_setup(db):
        pass  # role: fulkro

    service = LeadService(db)
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead = await service.create_lead(
        empresa_nombre="TestCo SL",
        contacto_email="contact@testco.es",
        sector="Industrial",
        origen="manual",
        temperature_level=5,
        categoria_objetivo_ens="MEDIA",
    )

    assert lead.id is not None
    assert lead.empresa_nombre == "TestCo SL"
    assert lead.contacto_email == "contact@testco.es"
    assert lead.origen == "manual"
    assert lead.estado_contacto == "nuevo"
    assert lead.temperature_level == 5
    assert lead.categoria_objetivo_ens == "MEDIA"

    # Audit trail row
    history = (await db.execute(
        select(LeadStageHistory).where(LeadStageHistory.lead_id == lead.id)
    )).scalar_one()
    assert history.estado_anterior is None
    assert history.estado_nuevo == "nuevo"
    assert history.metadata_jsonb["event"] == "lead_created"


@pytest.mark.asyncio
async def test_create_lead_dedup_idempotent(db):
    """create_lead retorna existing lead si email+origen duplicado."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    lead1 = await service.create_lead(
        empresa_nombre="Dup TestCo",
        contacto_email="dup@testco.es",
        origen="manual",
    )
    lead2 = await service.create_lead(
        empresa_nombre="Dup TestCo OTRO NOMBRE",  # different · debe ignorar
        contacto_email="dup@testco.es",
        origen="manual",
    )
    # Mismo objeto (idempotent dedup)
    assert lead1.id == lead2.id
    assert lead2.empresa_nombre == "Dup TestCo"  # NO update


@pytest.mark.asyncio
async def test_create_lead_invalid_estado_raises(db):
    """create_lead rechaza estado_contacto fuera VALID_TRANSITIONS."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    with pytest.raises(LeadServiceError):
        await service.create_lead(
            empresa_nombre="Bad State Co",
            contacto_email="bad@badco.es",
            estado_contacto="INVALID_STATE",
        )


# ====================== transition_estado_contacto ======================

@pytest.mark.asyncio
async def test_transition_estado_contacto_valid_progression(db):
    """transition válida nuevo → enviado · audit trail + side effect."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    lead = await service.create_lead(
        empresa_nombre="Progress Co",
        contacto_email="prog@progco.es",
    )
    assert lead.primer_contacto_at is None

    user_id = uuid.uuid4()
    lead = await service.transition_estado_contacto(
        lead_id=lead.id,
        target_estado="enviado",
        by_user_id=user_id,
        notes="Email cold outreach enviado",
    )
    assert lead.estado_contacto == "enviado"
    # Side effect: primer_contacto_at populated
    assert lead.primer_contacto_at is not None

    # Audit trail row creado
    history_rows = (await db.execute(
        select(LeadStageHistory)
        .where(LeadStageHistory.lead_id == lead.id)
        .order_by(LeadStageHistory.created_at)
    )).scalars().all()
    assert len(history_rows) == 2  # creation + transition
    assert history_rows[1].estado_anterior == "nuevo"
    assert history_rows[1].estado_nuevo == "enviado"
    assert history_rows[1].cambiado_por_user_id == user_id


@pytest.mark.asyncio
async def test_transition_invalid_raises(db):
    """transition inválida nuevo → ganado raises InvalidTransitionError."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    lead = await service.create_lead(
        empresa_nombre="Invalid Trans Co",
        contacto_email="inv@invco.es",
    )
    # nuevo → ganado NO está en VALID_TRANSITIONS["nuevo"]
    with pytest.raises(InvalidTransitionError) as exc_info:
        await service.transition_estado_contacto(
            lead_id=lead.id,
            target_estado="ganado",
        )
    assert "Transición inválida" in str(exc_info.value)
    assert "'nuevo'" in str(exc_info.value)
    assert "'ganado'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_transition_descartado_side_effects(db):
    """transition → descartado popula fecha_perdida + razon_perdida."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    lead = await service.create_lead(
        empresa_nombre="Lost Lead Co",
        contacto_email="lost@lostco.es",
    )
    lead = await service.transition_estado_contacto(
        lead_id=lead.id,
        target_estado="descartado",
        notes="No interesado tras 3 follow-ups",
    )
    assert lead.estado_contacto == "descartado"
    assert lead.fecha_perdida is not None
    assert lead.razon_perdida == "No interesado tras 3 follow-ups"


@pytest.mark.asyncio
async def test_transition_lead_not_found_raises(db):
    """transition con lead_id inexistente raises LeadNotFoundError."""
    service = LeadService(db)
    fake_id = uuid.uuid4()
    with pytest.raises(LeadNotFoundError):
        await service.transition_estado_contacto(
            lead_id=fake_id,
            target_estado="enviado",
        )


# ====================== list_pipeline ======================

@pytest.mark.asyncio
async def test_list_pipeline_filter_by_estado(db):
    """list_pipeline filtra por estado_contacto."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    await service.create_lead(
        empresa_nombre="Filter A",
        contacto_email="a@filter.es",
        origen="manual",
    )
    lead_b = await service.create_lead(
        empresa_nombre="Filter B",
        contacto_email="b@filter.es",
        origen="manual",
    )
    await service.transition_estado_contacto(
        lead_id=lead_b.id, target_estado="enviado",
    )

    nuevos = await service.list_pipeline(estado_contacto="nuevo")
    enviados = await service.list_pipeline(estado_contacto="enviado")
    assert any(l.empresa_nombre == "Filter A" for l in nuevos)
    assert all(l.estado_contacto == "nuevo" for l in nuevos)
    assert any(l.empresa_nombre == "Filter B" for l in enviados)


@pytest.mark.asyncio
async def test_list_pipeline_filter_by_origen(db):
    """list_pipeline filtra por origen."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    await service.create_lead(
        empresa_nombre="From manual",
        contacto_email="m@from.es",
        origen="manual",
    )
    await service.create_lead(
        empresa_nombre="From referido",
        contacto_email="r@from.es",
        origen="referido",
    )

    referidos = await service.list_pipeline(origen="referido")
    assert all(l.origen == "referido" for l in referidos)
    assert any(l.empresa_nombre == "From referido" for l in referidos)
