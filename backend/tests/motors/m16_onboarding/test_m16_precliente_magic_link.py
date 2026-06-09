"""Batch A diagnóstico previo · emisión magic-link account-less en create_session.

create_session(purpose=DIAGNOSTICO_PRECLIENTE) emite un magic-link (scope=session_id)
para que el LEAD responda SIN cuenta (flujo consume + /me/* existente). Default
(sin purpose) preserva el comportamiento in-portal ADR-020 v3 (magic_link_id=None).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.models.onboarding import OnboardingSession
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m16_onboarding.client_service import (
    consume_magic_link_and_start,
)
from backend.app.motors.m16_onboarding.enums import Role, Sector
from backend.app.motors.m16_onboarding.service import create_session
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_precliente_purpose_emits_magic_link_and_consume_finds_session(db):
    """Emisión + wiring end-to-end: el lead consume el link y localiza su sesión."""
    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    result = await create_session(
        db, project_id=project_id, sector=Sector.SERVICIOS_PROFESIONALES,
        role=Role.SPONSOR, interlocutor_email="lead@example.com",
        interlocutor_name="Lead Frío", ttl_hours=14 * 24, language="es",
        metadata_extra=None, purpose=MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
    )

    # Magic-link account-less emitido + persistido en la sesión.
    assert result["magic_link_id"] is not None
    assert result["magic_link_url"] and "token=" in result["magic_link_url"]
    onb = (await db.execute(
        select(OnboardingSession).where(OnboardingSession.id == result["session_id"])
    )).scalar_one()
    assert onb.magic_link_id == result["magic_link_id"]

    # End-to-end: el lead consume sin cuenta → scope.session_id localiza la
    # sesión + emite session_secret (el wiring que Batch B usará para /me/*).
    token = result["magic_link_url"].split("token=")[1]
    consume = await consume_magic_link_and_start(db, token, None)
    assert consume  # no raise · devuelve payload con session_secret
    onb2 = (await db.execute(
        select(OnboardingSession).where(OnboardingSession.id == result["session_id"])
    )).scalar_one()
    assert onb2.client_auth_secret_hash is not None  # consume emitió el secret


@pytest.mark.asyncio
async def test_default_no_purpose_preserves_in_portal_no_magic_link(db):
    """Sin purpose → magic_link_id None (ADR-020 v3 in-portal · NO regresión)."""
    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    result = await create_session(
        db, project_id=project_id, sector=Sector.SERVICIOS_PROFESIONALES,
        role=Role.SPONSOR, interlocutor_email="cliente@example.com",
        interlocutor_name="Cliente", ttl_hours=72, language="es",
        metadata_extra=None,
    )

    assert result["magic_link_id"] is None
    assert result["magic_link_url"] is None
    onb = (await db.execute(
        select(OnboardingSession).where(OnboardingSession.id == result["session_id"])
    )).scalar_one()
    assert onb.magic_link_id is None
