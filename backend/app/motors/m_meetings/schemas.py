"""Motor Meetings — Schemas Pydantic (sub-bloque 7.A.2).

Espejo del modelo ExploratoryMeetingRow + workflow operations.
Tipos compartidos via Literal (sincronizados con CHECK constraints
migration e8b3c5d70a91).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ────────────────────────────────────────────────────────────────────
# TYPE ALIASES — sincronizar con migration CHECK constraints
# ────────────────────────────────────────────────────────────────────

MeetingPlatform = Literal[
    "google_meet",
    "zoom",
    "teams",
    "presencial",
    "jitsi",
    "other",
]

MeetingEtapaK = Literal[
    "K.1", "K.2", "K.3", "K.4", "K.5", "K.6", "other",
]

MeetingStatus = Literal[
    "scheduled",
    "in_progress",
    "completed",
    "cancelled",
]

PostActionType = Literal[
    "propuesta",
    "create_project",
    "k6_signature",
    "email_summary",
]


# ────────────────────────────────────────────────────────────────────
# INPUT — create + update
# ────────────────────────────────────────────────────────────────────


class MeetingCreate(BaseModel):
    """Body POST /admin/meetings — create scheduled meeting."""

    client_id: uuid.UUID
    project_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=200)
    platform: MeetingPlatform | None = None
    meeting_url: str | None = Field(default=None, max_length=500)
    etapa_k: MeetingEtapaK | None = None
    interlocutor_contact_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "FK opcional client_contacts.id (M30). Si presente, se "
            "loggea interaction='meeting_attended' al complete_meeting."
        ),
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Mapped a columna ``meeting_date`` server-side.",
    )
    lead_source: str | None = Field(default=None, max_length=40)


class MeetingUpdate(BaseModel):
    """PATCH partial /admin/meetings/{id} — actualizaciones pre-completion.

    Sub-bloque 7.B.5: ``notes_markdown`` opcional autosave debounce 2s
    desde MeetingNotes frontend. Service render ``notes_html_sanitized``
    server-side al persistir.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    platform: MeetingPlatform | None = None
    meeting_url: str | None = Field(default=None, max_length=500)
    etapa_k: MeetingEtapaK | None = None
    interlocutor_contact_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    project_id: uuid.UUID | None = None
    notes_markdown: str | None = Field(default=None, max_length=100_000)


class MeetingComplete(BaseModel):
    """Body POST /admin/meetings/{id}/complete — completar meeting."""

    notes_markdown: str | None = Field(default=None, max_length=100_000)
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    outputs_agente_18: dict[str, Any] | None = Field(
        default=None,
        description="Output JSON A18 acumulado durante la reunión.",
    )


class MeetingCancel(BaseModel):
    """Body POST /admin/meetings/{id}/cancel."""

    reason: str | None = Field(default=None, max_length=500)


# ────────────────────────────────────────────────────────────────────
# POST-MEETING ACTIONS — 4 cross-motor
# ────────────────────────────────────────────────────────────────────


class MeetingPostActionRequest(BaseModel):
    """Body POST /admin/meetings/{id}/post-action.

    action_type:
      - ``propuesta`` → A19 RedactorPropuestasAgent → P-001 DOCX
      - ``create_project`` → Core projects service.create_project
      - ``k6_signature`` → M12 magic link FIRMA_DOCUMENTO
      - ``email_summary`` → EmailSender consolidado (template HTML)
    """

    action_type: PostActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class MeetingPostActionResponse(BaseModel):
    """Response post-action genérico (cada motor devuelve su payload)."""

    action_type: PostActionType
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


# ────────────────────────────────────────────────────────────────────
# OUTPUT — detail + list views
# ────────────────────────────────────────────────────────────────────


class MeetingContactSummary(BaseModel):
    """Mini-card interlocutor M30 (cuando interlocutor_contact_id presente)."""

    contact_id: uuid.UUID
    full_name: str
    role_title: str
    role_category: str
    email: str
    notes_excerpt: str | None = Field(
        default=None,
        description="Primeros 200 chars de notes_marcos del contacto.",
    )


class MeetingDetail(BaseModel):
    """Vista detalle meeting con interlocutor mini-card."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    project_id: uuid.UUID | None = None
    title: str
    platform: MeetingPlatform | None = None
    meeting_url: str | None = None
    etapa_k: MeetingEtapaK | None = None
    interlocutor_contact_id: uuid.UUID | None = None
    interlocutor: MeetingContactSummary | None = None

    meeting_date: datetime | None = None
    duration_minutes: int | None = None
    status: MeetingStatus
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None

    notes_markdown: str | None = None
    notes_html_sanitized: str | None = None

    sse_session_id: uuid.UUID | None = None
    outputs_agente_18: dict[str, Any] | None = Field(
        default=None,
        validation_alias="outputs_agente_18_jsonb",
    )

    lead_source: str | None = None
    conversion_status: str
    proposal_generated_id: uuid.UUID | None = None

    created_at: datetime | None = None


class MeetingListItem(BaseModel):
    """Compact view para listings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    project_id: uuid.UUID | None = None
    title: str
    platform: MeetingPlatform | None = None
    etapa_k: MeetingEtapaK | None = None
    interlocutor_contact_id: uuid.UUID | None = None
    interlocutor_name: str | None = Field(
        default=None,
        description="Resolved JOIN client_contacts.full_name.",
    )
    meeting_date: datetime | None = None
    status: MeetingStatus
    duration_minutes: int | None = None
    has_notes: bool = False


class MeetingSearchResult(BaseModel):
    """Result item de full-text search GIN sobre notes_markdown."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    meeting_date: datetime | None = None
    status: MeetingStatus
    snippet: str = Field(
        description="Primeros 200 chars notes_markdown que matcheó.",
    )


# ────────────────────────────────────────────────────────────────────
# SSE — A18 stream
# ────────────────────────────────────────────────────────────────────


class SSEStartResponse(BaseModel):
    """POST /admin/meetings/{id}/sse-init crea sse_session_id."""

    sse_session_id: uuid.UUID
    stream_url: str = Field(
        description=(
            "GET /api/v1/agents/18/meeting-update/stream/{sse_session_id} "
            "para consumer EventSource frontend."
        ),
    )
