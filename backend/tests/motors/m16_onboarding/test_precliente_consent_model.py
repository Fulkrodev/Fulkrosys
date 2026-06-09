"""Batch A diagnóstico previo · smoke del modelo dedicado de consentimiento del lead.

Append-only ledger · interés legítimo art. 6.1.f · versiona el texto Art. 13.
SIN RLS (escrito account-less por el lead · espejo onboarding_responses).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from backend.app.models.precliente_consent import PreClienteDiagnosticConsent
from backend.app.motors.m16_onboarding.enums import Role, Sector
from backend.app.motors.m16_onboarding.service import create_session
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_precliente_consent_insert_read_and_append_only(db):
    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    # Sesión de onboarding (FK del consent).
    sess = await create_session(
        db, project_id=project_id, sector=Sector.SERVICIOS_PROFESIONALES,
        role=Role.SPONSOR, interlocutor_email="lead@example.com",
        interlocutor_name="Lead", ttl_hours=72, language="es",
        metadata_extra=None,
    )
    session_id = sess["session_id"]

    # Registro de consentimiento (lo que escribe el lead al aceptar Art. 13).
    consent = PreClienteDiagnosticConsent(
        onboarding_session_id=session_id,
        interlocutor_email="lead@example.com",
        consent_text_version="v1",
        consented=True,
        consent_scope="diagnostic_questionnaire_data_processing",
        consented_at=datetime.now(timezone.utc),
        ip_address="203.0.113.7",
        user_agent="Mozilla/5.0 (Test)",
    )
    db.add(consent)
    await db.flush()
    await db.refresh(consent)  # carga server_default legal_basis

    # Read-back + defaults.
    assert consent.consent_text_version == "v1"
    assert consent.legal_basis == "interes_legitimo_art_6_1_f"  # server_default
    assert consent.consented is True
    assert str(consent.ip_address) == "203.0.113.7"

    # Append-only: un 2º registro NO sobrescribe · quedan 2 filas.
    db.add(PreClienteDiagnosticConsent(
        onboarding_session_id=session_id,
        consent_text_version="v1",
        consented=True,
        consented_at=datetime.now(timezone.utc),
    ))
    await db.flush()
    count = (await db.execute(
        select(func.count()).select_from(PreClienteDiagnosticConsent)
        .where(PreClienteDiagnosticConsent.onboarding_session_id == session_id)
    )).scalar()
    assert count == 2
