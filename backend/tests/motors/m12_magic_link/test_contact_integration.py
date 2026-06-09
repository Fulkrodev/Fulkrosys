"""Tests integración M12 ↔ M30: magic_links.sent_to_contact_id FK +
log_interaction post-consume (TODO-M30-M12-INTEGRATION-001 RESOLVED).

BLOQUE 3 BAJAS pre-FASE 6. Patrón coherente con A18 (meeting), M14
(contract_signature) — auto-log interaction al timeline contacto cuando
el flow cross-motor se completa con un contact_id presente.

Cobertura:
1. Magic link generado con sent_to_contact_id → consume registra
   interaction_type='magic_link', source_motor='m12' en timeline.
2. Magic link sin sent_to_contact_id → consume NO crea interaction
   (no efecto cross-motor).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context
from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import (
    MagicLinkConsumeRequest,
    MagicLinkGenerateRequest,
)
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.app.motors.m30_client_contacts.models import (
    ClientContactInteraction,
)
from backend.app.motors.m30_client_contacts.schemas import ClientContactCreate
from backend.app.motors.m30_client_contacts.service import ClientContactService
from backend.tests.conftest import setup_test_project

BASE_URL = "https://test.fulkro.es"


@pytest.mark.asyncio
async def test_magic_link_with_contact_logs_interaction(db: AsyncSession):
    """Magic link con sent_to_contact_id → consume loggea interaction
    'magic_link' en timeline del contacto (source_motor='m12')."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    contact_svc = ClientContactService(db)
    contact = await contact_svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Firmante M12 Integration",
            email="firmante-m12@example.com",
            role_title="CFO",
            role_category="sponsor",
            is_signatory=True,
        ),
    )

    svc = MagicLinkService(db)
    resp = await svc.generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=project_id,
            purpose=MagicLinkPurpose.PORTAL_REMEDIACION,
            recipient_email="firmante-m12@example.com",
            sent_to_contact_id=contact.id,
        ),
        base_url=BASE_URL,
    )
    await db.flush()

    link = await db.get(MagicLink, resp.magic_link_id)
    assert link.sent_to_contact_id == contact.id, (
        "FK sent_to_contact_id debe estar populated post-generate"
    )

    # Consume — debe loggear en timeline del contacto
    consume_resp = await svc.consume_magic_link(
        MagicLinkConsumeRequest(token=resp.token)
    )
    assert consume_resp.magic_link_id == resp.magic_link_id

    # Verificar interaction registrada en timeline M30
    timeline = await contact_svc.get_timeline(contact.id)
    assert len(timeline) == 1, (
        f"Esperaba 1 interaction post-consume, encontré {len(timeline)}"
    )
    entry = timeline[0]
    assert entry.interaction_type == "magic_link"
    assert entry.source_motor == "m12"
    assert entry.source_id == resp.magic_link_id
    assert entry.summary is not None
    assert "portal_remediacion" in entry.summary.lower()


@pytest.mark.asyncio
async def test_magic_link_without_contact_no_log(db: AsyncSession):
    """Magic link sin sent_to_contact_id → consume NO crea entry timeline
    (no efecto cross-motor cuando flow no involucra contacto registrado)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    # Crear contacto NO linkeado al magic link (control negativo)
    contact_svc = ClientContactService(db)
    contact = await contact_svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Contacto No Linkeado",
            email="no-link@example.com",
            role_title="CTO",
            role_category="cto",
        ),
    )

    svc = MagicLinkService(db)
    resp = await svc.generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=project_id,
            purpose=MagicLinkPurpose.PORTAL_REMEDIACION,
            recipient_email="anon@example.com",
            # sent_to_contact_id omitido — flow legacy
        ),
        base_url=BASE_URL,
    )
    await db.flush()

    link = await db.get(MagicLink, resp.magic_link_id)
    assert link.sent_to_contact_id is None

    await svc.consume_magic_link(MagicLinkConsumeRequest(token=resp.token))

    # 0 interactions linked al contact (no FK en magic_link).
    timeline = await contact_svc.get_timeline(contact.id)
    assert timeline == [], (
        f"Esperaba timeline vacío para contacto no linkeado, encontré "
        f"{len(timeline)} entries"
    )

    # Y 0 interactions con source_id = magic_link_id en toda la tabla.
    res = await db.execute(
        select(ClientContactInteraction).where(
            ClientContactInteraction.source_id == resp.magic_link_id,
        )
    )
    assert list(res.scalars()) == []
