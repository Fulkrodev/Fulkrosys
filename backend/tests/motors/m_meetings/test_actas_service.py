"""Tests ActasService · SAN-E v3.MB-6 atom 5 · Actas 4 tipos signable cliente.

10 tests cubren:
  Create + subtype enum:
    1. test_create_acta_draft_persists_subtype
    2. test_acta_subtype_other_allowed (sub-Q1)
    3. test_create_acta_invalid_subtype_raises
  Admin curation workflow:
    4. test_admin_curate_workflow_transitions
    5. test_admin_send_to_client_requires_curated
  List + subtype filter (Q5 + sub-Q3):
    6. test_list_for_client_filters_sent_to_client_only
    7. test_list_for_client_subtype_filter
  Cliente review (MixinA · 9a aplicacion):
    8. test_mark_client_review_blocked_until_sent
  Document hash + signoff (sub-Q2 multi-sig):
    9. test_compute_acta_hash_deterministic
   10. test_process_signoff_appends_to_firmas_jsonb_and_sets_workflow
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.governance import CommitteeMeeting
from backend.app.motors.m_meetings.actas_service import (
    ActaAlreadySignedError,
    ActasError,
    ActasService,
    InvalidActaSubtypeError,
    InvalidWorkflowTransitionError,
)
from backend.tests.conftest import setup_test_project


def _asistentes_min() -> list[dict]:
    return [
        {"nombre": "Marcos Mata", "cargo": "RSI", "email": "marcos@test.es"},
        {"nombre": "Cliente Resp", "cargo": "CISO", "email": "cliente@test.es"},
    ]


async def _create_draft(
    svc: ActasService,
    project_id: uuid.UUID,
    *,
    subtype: str = "kickoff",
    admin_user_id: uuid.UUID | None = None,
) -> CommitteeMeeting:
    return await svc.create_acta_draft(
        project_id=project_id,
        acta_subtype=subtype,
        titulo=f"Acta {subtype}",
        fecha=date(2026, 5, 11),
        presidente="Marcos Mata",
        secretario="Cliente Resp",
        asistentes=_asistentes_min(),
        admin_user_id=admin_user_id or uuid.uuid4(),
    )


# ════════════════════════════════════════════════════════════════════
# Create + subtype enum
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_acta_draft_persists_subtype(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)

    meeting = await _create_draft(svc, uuid.UUID(project_id), subtype="kickoff")

    assert meeting.id is not None
    assert meeting.acta_subtype == "kickoff"
    assert meeting.admin_curation_status == "draft"
    assert meeting.estado == "draft"
    assert meeting.codigo is not None and meeting.codigo.startswith("E-005-")
    assert meeting.tipo_comite == "kickoff"  # legacy coherence
    assert meeting.firmas == []
    assert meeting.client_signing_intent_id is None


@pytest.mark.asyncio
async def test_acta_subtype_other_allowed(db: AsyncSession):
    """Sub-Q1 · 'other' future-ready en enum 5 valores."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)

    meeting = await _create_draft(svc, uuid.UUID(project_id), subtype="other")

    assert meeting.acta_subtype == "other"
    assert meeting.tipo_comite == "extraordinario"  # mapped legacy


@pytest.mark.asyncio
async def test_create_acta_invalid_subtype_raises(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)

    with pytest.raises(InvalidActaSubtypeError):
        await _create_draft(
            svc, uuid.UUID(project_id), subtype="not_a_valid_subtype",
        )


# ════════════════════════════════════════════════════════════════════
# Admin curation workflow
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_curate_workflow_transitions(db: AsyncSession):
    """draft → curated_by_admin → sent_to_client transitions."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    admin_id = uuid.uuid4()

    meeting = await _create_draft(
        svc, uuid.UUID(project_id), subtype="checkpoint",
        admin_user_id=admin_id,
    )

    curated = await svc.admin_curate_acta(
        meeting_id=meeting.id,
        admin_user_id=admin_id,
        content_edits={"notas_libres": "Curated by Marcos"},
    )
    assert curated.admin_curation_status == "curated_by_admin"
    assert curated.admin_curated_at is not None
    assert curated.notas_libres == "Curated by Marcos"

    sent = await svc.admin_send_to_client(
        meeting_id=meeting.id, admin_user_id=admin_id,
    )
    assert sent.admin_curation_status == "sent_to_client"
    assert sent.enviada_at is not None


@pytest.mark.asyncio
async def test_admin_send_to_client_requires_curated(db: AsyncSession):
    """send_to_client desde draft directo · transition invalida."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    admin_id = uuid.uuid4()

    meeting = await _create_draft(svc, uuid.UUID(project_id), admin_user_id=admin_id)

    with pytest.raises(InvalidWorkflowTransitionError):
        await svc.admin_send_to_client(
            meeting_id=meeting.id, admin_user_id=admin_id,
        )


# ════════════════════════════════════════════════════════════════════
# List + subtype filter (Q5 + sub-Q3)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_for_client_filters_sent_to_client_only(db: AsyncSession):
    """Q5 · cliente VE solo admin_curation_status='sent_to_client'."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    admin_id = uuid.uuid4()
    pid = uuid.UUID(project_id)

    # Acta 1 · stuck en draft (NO visible cliente)
    await _create_draft(svc, pid, subtype="kickoff", admin_user_id=admin_id)

    # Acta 2 · advancada hasta sent_to_client (visible cliente)
    m2 = await _create_draft(svc, pid, subtype="audit", admin_user_id=admin_id)
    await svc.admin_curate_acta(meeting_id=m2.id, admin_user_id=admin_id)
    await svc.admin_send_to_client(meeting_id=m2.id, admin_user_id=admin_id)

    listed = await svc.list_actas_for_client(project_id=pid)
    assert len(listed) == 1
    assert listed[0].id == m2.id
    assert listed[0].acta_subtype == "audit"


@pytest.mark.asyncio
async def test_list_for_client_subtype_filter(db: AsyncSession):
    """Sub-Q3 · subtype chip selector filter optional."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    admin_id = uuid.uuid4()
    pid = uuid.UUID(project_id)

    async def _advance_to_sent(subtype: str) -> uuid.UUID:
        m = await _create_draft(svc, pid, subtype=subtype, admin_user_id=admin_id)
        await svc.admin_curate_acta(meeting_id=m.id, admin_user_id=admin_id)
        await svc.admin_send_to_client(meeting_id=m.id, admin_user_id=admin_id)
        return m.id

    m_kick = await _advance_to_sent("kickoff")
    m_check = await _advance_to_sent("checkpoint")
    await _advance_to_sent("audit")

    only_kick = await svc.list_actas_for_client(project_id=pid, subtype_filter="kickoff")
    assert {m.id for m in only_kick} == {m_kick}

    only_check = await svc.list_actas_for_client(project_id=pid, subtype_filter="checkpoint")
    assert {m.id for m in only_check} == {m_check}

    all_three = await svc.list_actas_for_client(project_id=pid)
    assert len(all_three) == 3


# ════════════════════════════════════════════════════════════════════
# Cliente review (MixinA · 9a aplicacion)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mark_client_review_blocked_until_sent(db: AsyncSession):
    """Cliente review NO permitido hasta admin_curation_status='sent_to_client'."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    admin_id = uuid.uuid4()
    user_id = uuid.uuid4()

    meeting = await _create_draft(
        svc, uuid.UUID(project_id), admin_user_id=admin_id,
    )

    with pytest.raises(ActasError):
        await svc.mark_client_review(
            meeting_id=meeting.id, action="revisada_ok", note=None, user_id=user_id,
        )

    # Avanzar workflow + intentar review · debe pasar
    await svc.admin_curate_acta(meeting_id=meeting.id, admin_user_id=admin_id)
    await svc.admin_send_to_client(meeting_id=meeting.id, admin_user_id=admin_id)

    reviewed = await svc.mark_client_review(
        meeting_id=meeting.id, action="revisada_ok",
        note=None, user_id=user_id,
    )
    assert reviewed.client_review_status == "revisada_ok"
    assert reviewed.client_reviewed_at is not None
    assert reviewed.client_reviewed_by_user_id == user_id


# ════════════════════════════════════════════════════════════════════
# Document hash + signoff (sub-Q2 multi-sig)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_compute_acta_hash_deterministic(db: AsyncSession):
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    meeting = await _create_draft(svc, uuid.UUID(project_id))

    h1, len1 = await svc.compute_acta_hash(meeting.id)
    h2, len2 = await svc.compute_acta_hash(meeting.id)

    assert len(h1) == 64  # SHA-256 hex
    assert h1 == h2
    assert len1 == len2 and len1 > 0


@pytest.mark.asyncio
async def test_process_signoff_appends_to_firmas_jsonb_and_sets_workflow(
    db: AsyncSession,
):
    """Sub-Q2 · firmas jsonb multi-sig + estado=fully_signed transition."""
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    admin_id = uuid.uuid4()
    user_id = uuid.uuid4()
    signing_intent_id = uuid.uuid4()

    meeting = await _create_draft(
        svc, uuid.UUID(project_id), subtype="cierre", admin_user_id=admin_id,
    )
    await svc.admin_curate_acta(meeting_id=meeting.id, admin_user_id=admin_id)
    await svc.admin_send_to_client(meeting_id=meeting.id, admin_user_id=admin_id)
    await svc.mark_client_review(
        meeting_id=meeting.id, action="revisada_ok", note=None, user_id=user_id,
    )

    signed = await svc.process_acta_signoff(
        meeting_id=meeting.id, signing_intent_id=signing_intent_id,
    )

    assert signed.client_signing_intent_id == signing_intent_id
    assert signed.estado == "fully_signed"
    assert signed.fully_signed_at is not None
    assert isinstance(signed.firmas, list) and len(signed.firmas) == 1
    cliente_firma = signed.firmas[0]
    assert cliente_firma["actor"] == "cliente"
    assert cliente_firma["signing_intent_id"] == str(signing_intent_id)
    assert cliente_firma["firmado_at"]

    # Idempotency · re-firmar mismo intent debe fallar
    with pytest.raises(ActaAlreadySignedError):
        await svc.process_acta_signoff(
            meeting_id=meeting.id, signing_intent_id=uuid.uuid4(),
        )


# ════════════════════════════════════════════════════════════════════
# F0-4 · Cadencia comité (P10-F07)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_evaluate_comite_cadence_no_actas_alerts(db: AsyncSession):
    """F0-4 (Ejecutable 8 Pasada 16 · P10-F07): sin actas de comité firmadas →
    alerta pre-auditoría + no cumple cadencia."""
    from backend.app.motors.m_meetings.actas_service import evaluate_comite_cadence
    _, project_id = await setup_test_project(db)
    rep = await evaluate_comite_cadence(db, uuid.UUID(project_id))
    assert rep["total_actas_firmadas"] == 0
    assert rep["cumple_cadencia"] is False
    assert rep["alerta_pre_auditoria"] is True
    assert rep["periodicidad_meses"] in (3, 6)  # trimestral o semestral


@pytest.mark.asyncio
async def test_evaluate_comite_cadence_recent_signed_ok(db: AsyncSession):
    """F0-4: acta de comité firmada reciente → cumple cadencia, sin alerta."""
    from datetime import UTC, datetime as _dt
    from backend.app.motors.m_meetings.actas_service import evaluate_comite_cadence
    _, project_id = await setup_test_project(db)
    svc = ActasService(db)
    acta = await _create_draft(svc, uuid.UUID(project_id))
    acta.estado = "fully_signed"
    acta.fecha = _dt.now(UTC)
    await db.flush()
    rep = await evaluate_comite_cadence(db, uuid.UUID(project_id))
    assert rep["total_actas_firmadas"] == 1
    assert rep["cumple_cadencia"] is True
    assert rep["alerta_pre_auditoria"] is False
