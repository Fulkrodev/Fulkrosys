"""Tests SAN-D MB-19.16 cosecha B · GET /commercial/leads/{id} detail.

Cubre DEC-MB19A-LEAD-DETAIL-PAGE asignado MB-19.C:
- Endpoint retorna {lead, stage_history, proposals, contract}
- Stage history ordered created_at DESC
- Proposals ordered version DESC
- Contract null si no existe
- 404 si lead no existe
- Lead serializado con campos extension MB-19.1

Refs: ADR-041 · MB-19.16 cosecha B.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.motors.m13_commercial.api import get_lead_detail
from backend.app.motors.m13_commercial.services.lead_service import LeadService
from backend.tests.conftest import _admin_setup


# ====================== Helpers ======================

async def _setup_lead_with_history_and_proposals(db, *, with_contract=False):
    """Helper crea lead M13 con stage history + proposal v1/v2 + opcional contract."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    lead = await service.create_lead(
        empresa_nombre="Detail Test Co",
        contacto_email=f"detail-{uuid.uuid4().hex[:6]}@detailco.es",
        empresa_cif=f"B{uuid.uuid4().hex[:8].upper()}",
        sector="Tecnología",
        categoria_objetivo_ens="MEDIA",
        archetype_ens="pyme_tecnologica",
        temperature_level=6,
    )

    # Trigger 2 transitions (audit history)
    await service.transition_estado_contacto(
        lead_id=lead.id, target_estado="enviado",
        notes="Email cold outreach",
    )
    await service.transition_estado_contacto(
        lead_id=lead.id, target_estado="respondio",
        notes="Cliente respondió email",
    )

    # Crear 2 proposals (v1 superseded + v2 active)
    proposal_v1_id = uuid.uuid4()
    proposal_v2_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO proposals (id, lead_id, version, "
        "categoria_objetivo, importe_total, estado, "
        "superseded, created_at) "
        "VALUES (:id, :lid, 1, 'MEDIA', 9500, "
        "'superseded', TRUE, now() - INTERVAL '2 days')"
    ), {"id": str(proposal_v1_id), "lid": str(lead.id)})
    await db.execute(text(
        "INSERT INTO proposals (id, lead_id, version, "
        "categoria_objetivo, importe_total, estado, "
        "feedback_cliente, cambios_desde_anterior, "
        "superseded, created_at) "
        "VALUES (:id, :lid, 2, 'MEDIA', 8500, 'sent', "
        "'Cliente solicita reducción precio 10%', "
        "'Reducción importe -1000€', "
        "FALSE, now())"
    ), {"id": str(proposal_v2_id), "lid": str(lead.id)})

    contract_id = None
    if with_contract:
        contract_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO contracts (id, lead_id, proposal_id, estado, "
            "tipo, cliente_firmante_nombre, "
            "firmado_marcos_at, firmado_cliente_at, "
            "created_at) "
            "VALUES (:id, :lid, :pid, 'signed', 'servicios', "
            "'Cliente Firmante Test', "
            "now() - INTERVAL '1 day', now(), "
            "now() - INTERVAL '1 day')"
        ), {
            "id": str(contract_id),
            "lid": str(lead.id),
            "pid": str(proposal_v2_id),
        })

    await db.flush()
    return lead, proposal_v1_id, proposal_v2_id, contract_id


# ====================== Tests endpoint ======================

@pytest.mark.asyncio
async def test_get_lead_detail_returns_complete_shape(db):
    """Endpoint retorna lead + stage_history + proposals + contract."""
    lead, _, _, _ = await _setup_lead_with_history_and_proposals(db)

    response = await get_lead_detail(lead_id=lead.id, db=db)

    assert "lead" in response
    assert "stage_history" in response
    assert "proposals" in response
    assert "contract" in response

    # Lead serialized correctamente
    assert response["lead"]["id"] == str(lead.id)
    assert response["lead"]["empresa"] == "Detail Test Co"
    assert response["lead"]["estado_contacto"] == "respondio"
    assert response["lead"]["categoria_objetivo_ens"] == "MEDIA"
    assert response["lead"]["temperature_level"] == 6
    assert response["lead"]["archetype_ens"] == "pyme_tecnologica"


@pytest.mark.asyncio
async def test_get_lead_detail_stage_history_desc_ordered(db):
    """stage_history ordered created_at DESC · más reciente primero."""
    lead, _, _, _ = await _setup_lead_with_history_and_proposals(db)

    response = await get_lead_detail(lead_id=lead.id, db=db)

    history = response["stage_history"]
    # 3 transiciones (creación + enviado + respondio)
    assert len(history) == 3

    # Última transition primero (respondio)
    assert history[0]["estado_nuevo"] == "respondio"
    assert history[0]["estado_anterior"] == "enviado"
    assert history[0]["notas"] == "Cliente respondió email"

    # Segunda transition (enviado)
    assert history[1]["estado_nuevo"] == "enviado"
    assert history[1]["estado_anterior"] == "nuevo"

    # Primera (creación · estado_anterior=None)
    assert history[2]["estado_nuevo"] == "nuevo"
    assert history[2]["estado_anterior"] is None


@pytest.mark.asyncio
async def test_get_lead_detail_proposals_version_desc(db):
    """proposals ordered version DESC · revisión más reciente primero."""
    lead, p1_id, p2_id, _ = await _setup_lead_with_history_and_proposals(db)

    response = await get_lead_detail(lead_id=lead.id, db=db)

    proposals = response["proposals"]
    assert len(proposals) == 2

    # v2 first
    assert proposals[0]["version"] == 2
    assert proposals[0]["id"] == str(p2_id)
    assert proposals[0]["superseded"] is False
    assert proposals[0]["estado"] == "sent"
    assert proposals[0]["importe_total"] == 8500.0
    assert proposals[0]["feedback_cliente"] == "Cliente solicita reducción precio 10%"

    # v1 second · superseded
    assert proposals[1]["version"] == 1
    assert proposals[1]["id"] == str(p1_id)
    assert proposals[1]["superseded"] is True
    assert proposals[1]["estado"] == "superseded"


@pytest.mark.asyncio
async def test_get_lead_detail_contract_present_when_signed(db):
    """contract field populated si lead tiene contrato asociado."""
    lead, _, p2_id, contract_id = await _setup_lead_with_history_and_proposals(
        db, with_contract=True,
    )

    response = await get_lead_detail(lead_id=lead.id, db=db)

    contract = response["contract"]
    assert contract is not None
    assert contract["id"] == str(contract_id)
    assert contract["estado"] == "signed"
    assert contract["tipo"] == "servicios"
    assert contract["cliente_firmante_nombre"] == "Cliente Firmante Test"
    assert contract["firmado_marcos_at"] is not None
    assert contract["firmado_cliente_at"] is not None


@pytest.mark.asyncio
async def test_get_lead_detail_contract_null_when_absent(db):
    """contract: null si lead no tiene contrato (lead pre-firma)."""
    lead, _, _, _ = await _setup_lead_with_history_and_proposals(
        db, with_contract=False,
    )

    response = await get_lead_detail(lead_id=lead.id, db=db)
    assert response["contract"] is None


@pytest.mark.asyncio
async def test_get_lead_detail_404_nonexistent_lead(db):
    """Endpoint raises 404 si lead UUID no existe."""
    fake_lead_id = uuid.uuid4()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_lead_detail(lead_id=fake_lead_id, db=db)
    assert exc_info.value.status_code == 404
    assert "no encontrado" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_lead_detail_no_proposals_returns_empty_list(db):
    """Lead sin proposals · proposals=[] válido."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)
    lead = await service.create_lead(
        empresa_nombre="No Proposals Co",
        contacto_email="np@np.es",
    )

    response = await get_lead_detail(lead_id=lead.id, db=db)
    assert response["proposals"] == []
    assert response["contract"] is None
    # Stage history al menos creación
    assert len(response["stage_history"]) >= 1
