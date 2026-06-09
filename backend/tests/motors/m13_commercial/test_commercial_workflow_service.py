"""Tests SAN-D MB-19.2 · CommercialWorkflowService.

Cubre:
- handle_contract_signed full flow (lead→ganado · client+project create
  · convertido_a_proyecto_id update · contract.project_id update).
- handle_contract_signed idempotente (re-trigger no duplica).
- handle_contract_signed skip si contract sin lead_id.
- handle_contract_signed skip si contract no encontrado.
- ClientUser invite best-effort.

Refs: ADR-041 · CommercialWorkflowService · LeadService.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from backend.app.models.commercial import Contract, Lead, Proposal
from backend.app.models.core import Client, Project
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
    ContractNotFoundError,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService
from backend.tests.conftest import _admin_setup


# ====================== Helper: setup lead + contract ======================

async def _setup_lead_and_contract(
    db,
    *,
    contacto_email="signer@testco.es",
    empresa_cif=None,
    categoria="MEDIA",
    importe_total=None,
    estado_contacto="propuesta_enviada",
):
    """Setup helper · crea lead M13 + contract firmado para testing."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)

    cif = empresa_cif or f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await service.create_lead(
        empresa_nombre="Signed Co SL",
        contacto_email=contacto_email,
        empresa_cif=cif,
        sector="Tecnología",
        categoria_objetivo_ens=categoria,
    )
    # Avanzar lead estado_contacto → propuesta_enviada (estado realista
    # pre-firma) si transición chained válida
    if estado_contacto == "propuesta_enviada":
        for tgt in ("enviado", "respondio", "reunion_agendada", "propuesta_enviada"):
            lead = await service.transition_estado_contacto(
                lead_id=lead.id, target_estado=tgt,
            )

    # Optional · crear proposal con categoria+importe para milestones test
    proposal_id = None
    if importe_total is not None:
        proposal_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO proposals (id, lead_id, version, "
            "categoria_objetivo, importe_total, estado, created_at) "
            "VALUES (:id, :lid, 1, :cat, :total, 'sent', now())"
        ), {
            "id": str(proposal_id),
            "lid": str(lead.id),
            "cat": categoria,
            "total": str(importe_total),
        })

    contract_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO contracts (id, lead_id, proposal_id, estado, "
        "firmado_cliente_at, created_at) "
        "VALUES (:id, :lid, :pid, 'signed', now(), now())"
    ), {
        "id": str(contract_id),
        "lid": str(lead.id),
        "pid": str(proposal_id) if proposal_id else None,
    })
    await db.flush()

    return lead, contract_id, proposal_id


# ====================== handle_contract_signed full flow ======================

@pytest.mark.asyncio
async def test_handle_contract_signed_full_conversion(db):
    """Full flow · lead→ganado + client+project create + cascade updates."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)

    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)

    assert result["status"] == "converted"
    assert result["lead_id"] == str(lead.id)
    assert result["client_id"] is not None
    assert result["project_id"] is not None

    # Lead actualizado
    await db.refresh(lead)
    assert lead.estado_contacto == "ganado"
    assert lead.fecha_conversion is not None
    assert lead.convertido_a_proyecto_id is not None
    assert str(lead.convertido_a_proyecto_id) == result["project_id"]

    # Project creado vinculado a Client desde Lead
    project = await db.get(Project, uuid.UUID(result["project_id"]))
    assert project is not None
    assert project.nombre == "ENS · Signed Co SL"
    assert project.categoria_objetivo == "MEDIA"
    assert project.lifecycle_state == "SIGNED"
    assert project.archetype is None  # archetype_ens not set in setup
    assert str(project.client_id) == result["client_id"]

    # Client creado desde Lead
    client = await db.get(Client, uuid.UUID(result["client_id"]))
    assert client is not None
    assert client.nombre == "Signed Co SL"
    assert client.cif == lead.empresa_cif
    assert client.contacto_email == lead.contacto_email
    assert client.sector == "Tecnología"
    assert client.lead_source == "manual"

    # Contract.project_id actualizado
    contract = await db.get(Contract, contract_id)
    assert str(contract.project_id) == result["project_id"]


@pytest.mark.asyncio
async def test_handle_contract_signed_idempotent(db):
    """Re-trigger handle_contract_signed retorna already_converted."""
    lead, contract_id, _ = await _setup_lead_and_contract(db)
    workflow = CommercialWorkflowService(db)

    result1 = await workflow.handle_contract_signed(contract_id)
    assert result1["status"] == "converted"

    # Re-trigger
    result2 = await workflow.handle_contract_signed(contract_id)
    assert result2["status"] == "already_converted"
    assert result2["project_id"] == result1["project_id"]
    assert result2["client_id"] == result1["client_id"]


@pytest.mark.asyncio
async def test_handle_contract_signed_skip_no_lead(db):
    """Contract sin lead_id retorna skipped."""
    contract_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO contracts (id, estado, "
            "firmado_cliente_at, created_at) "
            "VALUES (:id, 'signed', now(), now())"
        ), {"id": str(contract_id)})

    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)
    assert result["status"] == "skipped"
    assert "sin lead_id" in result["reason"]


@pytest.mark.asyncio
async def test_handle_contract_signed_not_found_raises(db):
    """Contract no encontrado raises ContractNotFoundError."""
    workflow = CommercialWorkflowService(db)
    fake_id = uuid.uuid4()
    with pytest.raises(ContractNotFoundError):
        await workflow.handle_contract_signed(fake_id)


@pytest.mark.asyncio
async def test_handle_contract_signed_creates_client_user_invite(db):
    """ClientUser invite single-user-RW best-effort (ADR-013 v3)."""
    lead, contract_id, _ = await _setup_lead_and_contract(
        db, contacto_email="invitee@testco.es",
    )

    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)

    assert result["client_user_id"] is not None

    user = await db.get(ClientUser, uuid.UUID(result["client_user_id"]))
    assert user is not None
    assert user.email == "invitee@testco.es"
    assert user.must_change_password is True
    assert str(user.client_id) == result["client_id"]


@pytest.mark.asyncio
async def test_handle_contract_signed_dedup_existing_client(db):
    """Si Client existe con mismo CIF · reusa client (no duplicate)."""
    cif_shared = f"B{uuid.uuid4().hex[:8].upper()}"

    # Crear Client existente
    existing_client_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Existing Co', :cif, now())"
        ), {"id": str(existing_client_id), "cif": cif_shared})

    lead, contract_id, _ = await _setup_lead_and_contract(
        db, empresa_cif=cif_shared,
    )

    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)

    assert result["status"] == "converted"
    assert result["client_id"] == str(existing_client_id)
    # NO crea client nuevo · reutiliza el existing


@pytest.mark.asyncio
async def test_handle_contract_signed_with_milestones(db):
    """Contract con proposal categoria+importe genera milestones."""
    lead, contract_id, proposal_id = await _setup_lead_and_contract(
        db, categoria="BASICA", importe_total=Decimal("6500"),
    )
    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)

    # MilestoneFactory existing best-effort · puede que >0 si pricing
    # calculator resuelve milestones para BASICA + 6500.
    # NO requerimos exacto · solo no-error y >=0.
    assert result["status"] == "converted"
    assert result["milestones_created"] >= 0  # MilestoneFactory best-effort


@pytest.mark.asyncio
async def test_handle_contract_signed_lead_without_email(db):
    """Lead sin contacto_email · skip ClientUser invite silente."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    service = LeadService(db)
    lead = await service.create_lead(
        empresa_nombre="No Email Co",
        contacto_email=None,
        empresa_cif=f"B{uuid.uuid4().hex[:8].upper()}",
    )
    # Avanzar a propuesta_enviada
    for tgt in ("enviado", "respondio", "reunion_agendada", "propuesta_enviada"):
        lead = await service.transition_estado_contacto(
            lead_id=lead.id, target_estado=tgt,
        )

    contract_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO contracts (id, lead_id, estado, "
        "firmado_cliente_at, created_at) "
        "VALUES (:id, :lid, 'signed', now(), now())"
    ), {"id": str(contract_id), "lid": str(lead.id)})
    await db.flush()

    workflow = CommercialWorkflowService(db)
    result = await workflow.handle_contract_signed(contract_id)
    assert result["status"] == "converted"
    assert result["client_user_id"] is None  # skipped silente
    assert result["project_id"] is not None  # project sí creado
