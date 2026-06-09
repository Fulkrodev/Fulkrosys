"""Tests integraciones M30 ↔ A14 Copilot / A18 Reunión / M14 Contracts.

Sub-fase 5.5.F (plan v4.2 5.5.4.1, 5.5.4.2, 5.5.4.5).

Cobertura:
- A14: build_m30_contacts_section helper devuelve formato esperado.
- A18: MinutesService.create con interlocutor_contact_id auto-loggea
       interaction "meeting" en timeline contacto.
- M14: ContractService.generate_contract con signatory_contact_ids
       auto-loggea interaction "contract_signature" por signatario.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.models import (
    ClientContactInteraction,
)
from backend.app.motors.m30_client_contacts.schemas import ClientContactCreate
from backend.app.motors.m30_client_contacts.service import ClientContactService
from backend.tests.conftest import _admin_setup


async def _create_test_client(db: AsyncSession) -> uuid.UUID:
    """INSERT cliente sintético via _admin_setup (bypass RLS)."""
    from sqlalchemy import text

    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:id, :nombre, :cif, 'publico', now())"
            ),
            {"id": str(client_id), "nombre": "Cliente Integraciones",
             "cif": cif},
        )
    await db.flush()
    return client_id


# ════════════════════════════════════════════════════════════════════
# A14 Copilot integration
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a14_build_m30_contacts_section_returns_formatted_lines(
    db: AsyncSession,
):
    """build_m30_contacts_section devuelve formato '## Contexto cliente
    (Contactos M30)' con 1 línea por contacto activo."""
    from backend.app.agents.agent_14_copiloto.service import (
        _build_m30_contacts_section,
    )

    client_id = await _create_test_client(db)
    svc = ClientContactService(db)

    await svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Sponsor Test",
            email="sponsor@example.com",
            role_title="CFO",
            role_category="sponsor",
            is_primary=True,
        ),
    )
    await svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Firmante Test",
            email="firmante@example.com",
            role_title="General Counsel",
            role_category="legal",
            is_signatory=True,
        ),
    )

    section = await _build_m30_contacts_section(db, client_id)
    assert section.startswith("## Contexto cliente")
    assert "Sponsor Test" in section
    assert "[PRIMARY]" in section
    assert "Firmante Test" in section
    assert "[SIGNATORY]" in section


@pytest.mark.asyncio
async def test_a14_section_empty_when_no_active_contacts(
    db: AsyncSession,
):
    """Si cliente no tiene contactos activos, section es string vacío
    (no inyecta header)."""
    from backend.app.agents.agent_14_copiloto.service import (
        _build_m30_contacts_section,
    )

    client_id = await _create_test_client(db)
    section = await _build_m30_contacts_section(db, client_id)
    assert section == ""


# ════════════════════════════════════════════════════════════════════
# A18 Minutes integration
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a18_minutes_create_logs_interaction_to_m30(
    db: AsyncSession,
):
    """MinutesService.create con interlocutor_contact_id → interaction
    nueva en timeline contacto con interaction_type='meeting' +
    source_motor='a18' + source_id=meeting.id."""
    from sqlalchemy import text

    from backend.app.motors.m18_communication.minutes_service import (
        MinutesService,
    )

    from backend.app.database import set_tenant_context

    client_id = await _create_test_client(db)
    project_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Proj A18 Integ', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )

    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Interlocutor A18",
            email="interlocutor@example.com",
            role_title="CISO",
            role_category="ciso",
        ),
    )

    # Set RLS context para committee_meetings (project_isolation policy).
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    minutes_svc = MinutesService(db)
    meeting = await minutes_svc.create(
        project_id=project_id,
        tipo_comite="kickoff",
        titulo="Reunión kickoff M30 integration test",
        fecha=date.today(),
        presidente="Marcos Mata",
        secretario="Marcos Mata",
        asistentes=[{"nombre": "Interlocutor A18", "rol": "CISO"}],
        interlocutor_contact_id=contact.id,
    )

    # Verify interaction logged en M30 timeline
    timeline = await svc.get_timeline(contact.id)
    assert len(timeline) == 1
    entry = timeline[0]
    assert entry.interaction_type == "meeting"
    assert entry.source_motor == "a18"
    assert entry.source_id == meeting.id
    assert "kickoff" in (entry.summary or "")


@pytest.mark.asyncio
async def test_a18_minutes_no_log_when_contact_absent(
    db: AsyncSession,
):
    """MinutesService.create sin interlocutor_contact_id NO loggea
    interactions (no efecto cross-motor)."""
    from sqlalchemy import text

    from backend.app.motors.m18_communication.minutes_service import (
        MinutesService,
    )

    from backend.app.database import set_tenant_context

    client_id = await _create_test_client(db)
    project_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Proj A18 NoContact', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    minutes_svc = MinutesService(db)
    meeting = await minutes_svc.create(
        project_id=project_id,
        tipo_comite="kickoff",
        titulo="Reunión sin contacto",
        fecha=date.today(),
        presidente="Marcos",
        secretario="Marcos",
        asistentes=[{"nombre": "Marcos"}],
    )

    # 0 interactions creadas (no contact_id).
    res = await db.execute(
        select(ClientContactInteraction).where(
            ClientContactInteraction.source_id == meeting.id,
        )
    )
    assert list(res.scalars()) == []


# ════════════════════════════════════════════════════════════════════
# M14 Contracts integration
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_m14_contract_logs_signatory_interactions(
    db: AsyncSession,
):
    """ContractService.generate_contract con signatory_contact_ids →
    1 interaction por signatario en timeline (interaction_type=
    'contract_signature' + source_motor='m14')."""
    from sqlalchemy import text

    from backend.app.motors.m14_contracts.contract_service import (
        ContractService,
    )

    from backend.app.database import set_tenant_context

    client_id = await _create_test_client(db)
    project_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Proj M14 Integ', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = ClientContactService(db)
    sig1 = await svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Signatario Uno",
            email="sig1@example.com",
            role_title="CEO",
            role_category="sponsor",
            is_signatory=True,
        ),
    )
    sig2 = await svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Signatario Dos",
            email="sig2@example.com",
            role_title="General Counsel",
            role_category="legal",
            is_signatory=True,
        ),
    )

    # Crear lead + proposal won prereq m14 generate_contract
    from backend.app.models.commercial import Lead, Proposal

    lead = Lead(
        empresa_nombre="Cliente Integraciones",
        sector="publico_local",
        contacto_email="contact@example.com",
        estado="cualificado",
    )
    db.add(lead)
    await db.flush()

    proposal = Proposal(
        lead_id=lead.id,
        project_id=project_id,
        version=1,
        estado="won",
    )
    db.add(proposal)
    await db.flush()

    contract_svc = ContractService()
    contract = await contract_svc.generate_contract(
        db,
        proposal_id=proposal.id,
        project_id=project_id,
        plantilla_id="C-001",
        cliente_firmante_nombre="Signatario Uno",
        cliente_firmante_cargo="CEO",
        signatory_contact_ids=[sig1.id, sig2.id],
    )

    # Verify 2 interactions creadas (1 por signatario)
    timeline_sig1 = await svc.get_timeline(sig1.id)
    assert len(timeline_sig1) == 1
    assert timeline_sig1[0].interaction_type == "contract_signature"
    assert timeline_sig1[0].source_motor == "m14"
    assert timeline_sig1[0].source_id == contract.id

    timeline_sig2 = await svc.get_timeline(sig2.id)
    assert len(timeline_sig2) == 1
    assert timeline_sig2[0].interaction_type == "contract_signature"
    assert timeline_sig2[0].source_motor == "m14"
