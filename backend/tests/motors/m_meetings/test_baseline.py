"""Tests baseline Motor Meetings (sub-bloque 7.A.8 FASE 7).

8 tests cubren:
  CRUD + workflow:
   1. test_create_meeting_persists_with_metadata
   2. test_complete_meeting_renders_html_sanitized
   3. test_complete_meeting_with_contact_logs_m30 (cross-motor)
   4. test_cancel_meeting_idempotent
   5. test_update_completed_meeting_raises_state_error

  Search + histórica:
   6. test_search_fts_finds_matching
   7. test_get_meetings_by_client_resolves_interlocutor_name

  PostMeetingActions:
   8. test_post_action_email_summary_sends_via_emailsender
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_meetings.actions import dispatch_post_action
from backend.app.motors.m_meetings.schemas import (
    MeetingCancel,
    MeetingComplete,
    MeetingCreate,
    MeetingPostActionRequest,
    MeetingUpdate,
)
from backend.app.motors.m_meetings.service import (
    MeetingService,
    MeetingStateError,
)
from backend.app.motors.m30_client_contacts.schemas import (
    ClientContactCreate,
)
from backend.app.motors.m30_client_contacts.service import (
    ClientContactService,
)
from backend.tests.conftest import setup_test_project


async def _setup(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Crea cliente + proyecto, retorna (client_id, project_id) UUIDs."""
    client_id_str, project_id_str = await setup_test_project(db)
    return uuid.UUID(client_id_str), uuid.UUID(project_id_str)


# ════════════════════════════════════════════════════════════════════
# CRUD + workflow — 5 tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_meeting_persists_with_metadata(db: AsyncSession):
    client_id, project_id = await _setup(db)
    svc = MeetingService(db)
    payload = MeetingCreate(
        client_id=client_id,
        project_id=project_id,
        title="Kickoff cliente publico",
        platform="google_meet",
        meeting_url="https://meet.google.com/abc-defg-hij",
        etapa_k="K.1",
    )
    meeting = await svc.create_meeting(payload)

    assert meeting.client_id == client_id
    assert meeting.project_id == project_id
    assert meeting.title == "Kickoff cliente publico"
    assert meeting.platform == "google_meet"
    assert meeting.etapa_k == "K.1"
    assert meeting.status == "scheduled"
    assert meeting.completed_at is None


@pytest.mark.asyncio
async def test_complete_meeting_renders_html_sanitized(db: AsyncSession):
    client_id, _ = await _setup(db)
    svc = MeetingService(db)
    meeting = await svc.create_meeting(
        MeetingCreate(client_id=client_id, title="Test"),
    )
    completed = await svc.complete_meeting(
        meeting.id,
        MeetingComplete(
            notes_markdown="**Hola** <script>alert('xss')</script>\nLínea 2",
            duration_minutes=45,
        ),
    )
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.duration_minutes == 45
    # XSS escape: <script> → &lt;script&gt;
    assert "<script>" not in (completed.notes_html_sanitized or "")
    assert "&lt;script&gt;" in (completed.notes_html_sanitized or "")
    # Newlines → <br>
    assert "<br>" in (completed.notes_html_sanitized or "")


@pytest.mark.asyncio
async def test_complete_meeting_with_contact_logs_m30(db: AsyncSession):
    """Cross-motor M30: complete con interlocutor → log_interaction."""
    client_id, _ = await _setup(db)
    contact_svc = ClientContactService(db)
    contact = await contact_svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Sponsor Test",
            email="sponsor@example.com",
            role_title="CFO",
            role_category="sponsor",
        ),
    )

    svc = MeetingService(db)
    meeting = await svc.create_meeting(
        MeetingCreate(
            client_id=client_id,
            title="K.1 Reunión exploratoria",
            platform="zoom",
            etapa_k="K.4",
            interlocutor_contact_id=contact.id,
        ),
    )
    await svc.complete_meeting(
        meeting.id,
        MeetingComplete(notes_markdown="OK", duration_minutes=50),
    )

    # Verificar interaction registrada en M30 timeline
    timeline = await contact_svc.get_timeline(contact.id)
    assert len(timeline) == 1
    entry = timeline[0]
    assert entry.interaction_type == "meeting"
    assert entry.source_motor == "meetings"
    assert entry.source_id == meeting.id
    assert entry.summary == "K.1 Reunión exploratoria"
    assert entry.details["platform"] == "zoom"
    assert entry.details["etapa_k"] == "K.4"


@pytest.mark.asyncio
async def test_cancel_meeting_idempotent(db: AsyncSession):
    client_id, _ = await _setup(db)
    svc = MeetingService(db)
    meeting = await svc.create_meeting(
        MeetingCreate(client_id=client_id, title="Cancelar test"),
    )
    cancelled = await svc.cancel_meeting(
        meeting.id, MeetingCancel(reason="conflict"),
    )
    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_at is not None

    # Segunda llamada idempotente
    cancelled2 = await svc.cancel_meeting(
        meeting.id, MeetingCancel(reason="another"),
    )
    assert cancelled2.status == "cancelled"


@pytest.mark.asyncio
async def test_update_completed_meeting_raises_state_error(
    db: AsyncSession,
):
    client_id, _ = await _setup(db)
    svc = MeetingService(db)
    meeting = await svc.create_meeting(
        MeetingCreate(client_id=client_id, title="State test"),
    )
    await svc.complete_meeting(
        meeting.id, MeetingComplete(notes_markdown="done"),
    )
    with pytest.raises(MeetingStateError):
        await svc.update_meeting(
            meeting.id, MeetingUpdate(title="Cannot update"),
        )


# ════════════════════════════════════════════════════════════════════
# Search + histórica — 2 tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_fts_finds_matching(db: AsyncSession):
    client_id, _ = await _setup(db)
    svc = MeetingService(db)

    m1 = await svc.create_meeting(
        MeetingCreate(client_id=client_id, title="Reunion A"),
    )
    await svc.complete_meeting(
        m1.id,
        MeetingComplete(
            notes_markdown=(
                "Cliente solicita certificación ENS antes del kickoff."
            ),
        ),
    )
    m2 = await svc.create_meeting(
        MeetingCreate(client_id=client_id, title="Reunion B"),
    )
    await svc.complete_meeting(
        m2.id,
        MeetingComplete(notes_markdown="Hola buenas, sin keyword."),
    )

    results = await svc.search_meetings_fts(query="certificación")
    assert len(results) == 1
    assert results[0].id == m1.id
    assert "certificación" in results[0].snippet.lower()


@pytest.mark.asyncio
async def test_get_meetings_by_client_resolves_interlocutor_name(
    db: AsyncSession,
):
    client_id, _ = await _setup(db)
    contact_svc = ClientContactService(db)
    contact = await contact_svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Ana López (DPO)",
            email="ana@cliente.com",
            role_title="DPO",
            role_category="dpo",
        ),
    )
    svc = MeetingService(db)
    await svc.create_meeting(
        MeetingCreate(
            client_id=client_id,
            title="Con interlocutor",
            interlocutor_contact_id=contact.id,
        ),
    )
    await svc.create_meeting(
        MeetingCreate(client_id=client_id, title="Sin interlocutor"),
    )

    items = await svc.get_meetings_by_client(client_id)
    assert len(items) == 2
    with_contact = next(
        (i for i in items if i.interlocutor_contact_id == contact.id),
        None,
    )
    assert with_contact is not None
    assert with_contact.interlocutor_name == "Ana López (DPO)"
    without_contact = next(
        (i for i in items if i.interlocutor_contact_id is None),
        None,
    )
    assert without_contact is not None
    assert without_contact.interlocutor_name is None


# ════════════════════════════════════════════════════════════════════
# PostMeetingActions — 1 test
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_post_action_email_summary_sends_via_emailsender(
    db: AsyncSession,
):
    """email_summary action invoca EmailSender (mock backend) y persiste log."""
    from backend.app.core.email.sender import (
        get_email_sender,
        reset_email_sender,
    )

    reset_email_sender()  # asegurar fresh singleton
    sender = get_email_sender(force_backend="mock")
    assert sender.backend == "mock"

    client_id, _ = await _setup(db)
    contact_svc = ClientContactService(db)
    contact = await contact_svc.create_contact(
        client_id,
        ClientContactCreate(
            full_name="Receptor",
            email="receptor@cliente.com",
            role_title="CIO",
            role_category="cio",
        ),
    )
    svc = MeetingService(db)
    meeting = await svc.create_meeting(
        MeetingCreate(
            client_id=client_id,
            title="Resumen test",
            etapa_k="K.4",
            interlocutor_contact_id=contact.id,
        ),
    )
    completed = await svc.complete_meeting(
        meeting.id,
        MeetingComplete(notes_markdown="Notas resumen", duration_minutes=30),
    )

    response = await dispatch_post_action(
        db,
        completed,
        MeetingPostActionRequest(
            action_type="email_summary",
            payload={"extra_message": "Gracias por la sesión."},
        ),
    )
    reset_email_sender()  # restore singleton state for other tests

    assert response.success is True, response.error_message
    assert response.action_type == "email_summary"
    assert response.result["to"] == "receptor@cliente.com"
    assert response.result["backend_used"] == "mock"
    assert response.result["message_id"] is not None
