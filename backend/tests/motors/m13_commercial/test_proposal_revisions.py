"""Tests SAN-D MB-19.3 · ProposalService.generate_revision + extensions.

Cubre:
- generate_revision crea version+1 + supersede anterior + persist feedback.
- generate_revision con importe_override re-distribuye hitos proportionally.
- generate_revision sin proposal anterior raises ProposalError.
- mark_accepted setea estado=won + fecha_aceptacion.
- list_revisions retorna histórico ordenado version DESC.
- get_active_proposal retorna superseded=FALSE más reciente.

Refs: ADR-041 · ProposalService.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text

from backend.app.models.commercial import Proposal
from backend.app.motors.m13_commercial.proposal_service import (
    ProposalService,
    ProposalError,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService


# ====================== Helper: setup lead + proposal v1 ======================

async def _setup_lead_and_proposal_v1(
    db,
    *,
    importe_total=Decimal("9500.00"),
    categoria="MEDIA",
    pricing_model="media_hitos",
):
    """Crea lead M13 + proposal v1 sent · helper para revision tests."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead_service = LeadService(db)
    lead = await lead_service.create_lead(
        empresa_nombre="Revision Co",
        contacto_email=f"rev-{uuid.uuid4().hex[:6]}@revco.es",
        categoria_objetivo_ens=categoria,
    )

    proposal_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO proposals (id, lead_id, version, "
        "pricing_model_id, categoria_objetivo, "
        "importe_total, importe_desglose, hitos_pago, "
        "duracion_semanas, effort_marcos_horas, "
        "validez_hasta, estado, superseded, created_at) "
        "VALUES (:id, :lid, 1, :pm, :cat, "
        ":imp, :desglose, :hitos, "
        "12, 200, "
        "(now() + interval '30 days')::date, 'sent', FALSE, now())"
    ), {
        "id": str(proposal_id),
        "lid": str(lead.id),
        "pm": pricing_model,
        "cat": categoria,
        "imp": str(importe_total),
        "desglose": (
            '{"base": 9500, "iva_percent": 21, "iva_importe": 1995, '
            '"total_con_iva": 11495}'
        ),
        "hitos": (
            '{"hitos": ['
            '{"nombre": "Inicio", "pct": 30, "importe": 2850}, '
            '{"nombre": "Avance", "pct": 40, "importe": 3800}, '
            '{"nombre": "Cierre", "pct": 30, "importe": 2850}]}'
        ),
    })
    await db.flush()
    return lead, proposal_id


# ====================== generate_revision ======================

@pytest.mark.asyncio
async def test_generate_revision_supersede_previous(db):
    """generate_revision marca anterior superseded=TRUE + crea v2."""
    lead, proposal_v1_id = await _setup_lead_and_proposal_v1(db)
    service = ProposalService()

    revision = await service.generate_revision(
        db,
        lead_id=lead.id,
        feedback_cliente="Necesito reducir el alcance · quitemos sede 2",
        cambios_desde_anterior="Removida sede secundaria · -1500€",
    )

    # v2 creada con feedback
    assert revision.version == 2
    assert revision.estado == "draft"
    assert revision.superseded is False
    assert revision.feedback_cliente.startswith("Necesito reducir")
    assert revision.cambios_desde_anterior.startswith("Removida sede")

    # v1 marcada superseded
    v1 = await db.get(Proposal, proposal_v1_id)
    assert v1.superseded is True
    assert v1.estado == "superseded"


@pytest.mark.asyncio
async def test_generate_revision_with_importe_override_redistributes_hitos(db):
    """importe_override aplica re-proporción hitos manteniendo % originales."""
    lead, _ = await _setup_lead_and_proposal_v1(
        db, importe_total=Decimal("10000.00"),
    )
    service = ProposalService()

    revision = await service.generate_revision(
        db,
        lead_id=lead.id,
        feedback_cliente="Cliente solicita reducción precio 20%",
        importe_override=8000.00,  # 10000 → 8000
    )

    assert float(revision.importe_total) == 8000.00
    hitos = (revision.hitos_pago or {}).get("hitos") or []
    assert len(hitos) == 3
    # Hitos re-proporcionados manteniendo % (30/40/30)
    assert hitos[0]["pct"] == 30
    assert hitos[0]["importe"] == 2400.00  # 8000 * 30%
    assert hitos[1]["importe"] == 3200.00  # 8000 * 40%
    assert hitos[2]["importe"] == 2400.00  # 8000 * 30%
    # Suma hitos == importe_total (100%)
    assert sum(h["importe"] for h in hitos) == 8000.00

    # Desglose IVA recalculado
    desglose = revision.importe_desglose or {}
    assert desglose["base"] == 8000.00
    assert desglose["iva_importe"] == 1680.00  # 8000 * 21%
    assert desglose["total_con_iva"] == 9680.00
    assert desglose["importe_override_aplicado"] is True
    assert desglose["importe_anterior"] == 10000.00


@pytest.mark.asyncio
async def test_generate_revision_without_previous_raises(db):
    """Lead sin propuesta anterior · raises ProposalError."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service_lead = LeadService(db)
    lead = await service_lead.create_lead(
        empresa_nombre="No Proposal Co",
        contacto_email="no@noco.es",
    )

    service = ProposalService()
    with pytest.raises(ProposalError) as exc_info:
        await service.generate_revision(
            db,
            lead_id=lead.id,
            feedback_cliente="Feedback sin propuesta previa",
        )
    assert "no tiene propuesta active" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_revision_persist_agent_19_metadata(db):
    """agent_19_metadata persiste en revision (caso AI regenerate · MB-19+)."""
    lead, _ = await _setup_lead_and_proposal_v1(db)
    service = ProposalService()

    revision = await service.generate_revision(
        db,
        lead_id=lead.id,
        feedback_cliente="Cambiar duración a 16 semanas",
        agent_19_metadata={
            "agent_run_id": "run-revision-001",
            "tokens_input": 5234,
            "tokens_output": 1856,
            "model": "opus-4.7",
            "retry_count": 0,
        },
    )

    assert revision.agent_19_metadata == {
        "agent_run_id": "run-revision-001",
        "tokens_input": 5234,
        "tokens_output": 1856,
        "model": "opus-4.7",
        "retry_count": 0,
    }


@pytest.mark.asyncio
async def test_generate_revision_chained_v3(db):
    """Chained v1 → v2 → v3 · solo última active · resto superseded."""
    lead, proposal_v1_id = await _setup_lead_and_proposal_v1(db)
    service = ProposalService()

    v2 = await service.generate_revision(
        db,
        lead_id=lead.id,
        feedback_cliente="Primera revisión cliente",
    )
    v3 = await service.generate_revision(
        db,
        lead_id=lead.id,
        feedback_cliente="Segunda revisión cliente",
    )

    assert v2.version == 2
    assert v3.version == 3
    assert v3.superseded is False

    # v1 + v2 superseded · v3 active
    v1 = await db.get(Proposal, proposal_v1_id)
    v2_refreshed = await db.get(Proposal, v2.id)
    assert v1.superseded is True
    assert v2_refreshed.superseded is True
    assert v3.superseded is False


# ====================== mark_accepted ======================

@pytest.mark.asyncio
async def test_mark_accepted_sets_estado_won(db):
    """mark_accepted setea estado=won + fecha_aceptacion=NOW."""
    lead, proposal_v1_id = await _setup_lead_and_proposal_v1(db)
    service = ProposalService()

    proposal = await service.mark_accepted(db, proposal_v1_id)
    assert proposal.estado == "won"
    assert proposal.fecha_aceptacion is not None


@pytest.mark.asyncio
async def test_mark_accepted_proposal_not_found_raises(db):
    """mark_accepted con UUID inexistente raises ProposalError."""
    service = ProposalService()
    with pytest.raises(ProposalError):
        await service.mark_accepted(db, uuid.uuid4())


# ====================== list_revisions / get_active_proposal ======================

@pytest.mark.asyncio
async def test_list_revisions_ordered_version_desc(db):
    """list_revisions devuelve histórico ordenado version DESC."""
    lead, _ = await _setup_lead_and_proposal_v1(db)
    service = ProposalService()
    await service.generate_revision(
        db, lead_id=lead.id, feedback_cliente="r2",
    )
    await service.generate_revision(
        db, lead_id=lead.id, feedback_cliente="r3",
    )

    revisions = await service.list_revisions(db, lead.id)
    assert len(revisions) == 3
    assert revisions[0].version == 3
    assert revisions[1].version == 2
    assert revisions[2].version == 1


@pytest.mark.asyncio
async def test_get_active_proposal_returns_latest_non_superseded(db):
    """get_active_proposal devuelve solo superseded=FALSE más reciente."""
    lead, _ = await _setup_lead_and_proposal_v1(db)
    service = ProposalService()
    await service.generate_revision(
        db, lead_id=lead.id, feedback_cliente="r2",
    )
    v3 = await service.generate_revision(
        db, lead_id=lead.id, feedback_cliente="r3",
    )

    active = await service.get_active_proposal(db, lead.id)
    assert active is not None
    assert active.id == v3.id
    assert active.version == 3
    assert active.superseded is False


@pytest.mark.asyncio
async def test_get_active_proposal_none_if_no_proposals(db):
    """get_active_proposal None si lead sin propuestas."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead_service = LeadService(db)
    lead = await lead_service.create_lead(
        empresa_nombre="Empty Co",
        contacto_email="empty@empty.es",
    )

    service = ProposalService()
    active = await service.get_active_proposal(db, lead.id)
    assert active is None
