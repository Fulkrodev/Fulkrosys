"""Motor Meetings — service core (sub-bloque 7.A.3).

Servicio CRUD + workflow + cross-motor M30 log_interaction.

Métodos:
  - CRUD: ``create_meeting``, ``list_meetings``, ``get_meeting_by_id``,
    ``update_meeting``, ``soft_delete_meeting``.
  - Workflow: ``complete_meeting`` (sets status + notes_html_sanitized
    + invoca M30 log_interaction si interlocutor presente),
    ``cancel_meeting``.
  - Search: ``search_meetings_fts`` (GIN español sobre notes_markdown).
  - Vista histórica: ``get_meetings_by_client``.
  - SSE: ``init_sse_session`` (genera UUID + persiste en row).

Pattern coherente con M29 ClientMessagingService + M30 ClientContactService.
HTML render: ``_render_safe_html`` espejo M29 (defensa profunda sin
nuevas deps; render real markdown sucede client-side via react-markdown
+ rehype-sanitize plan v4.2 6.31).
"""
from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.conformity_lifecycle import ExploratoryMeetingRow
from backend.app.motors.m30_client_contacts.models import ClientContact
from backend.app.motors.m_meetings.schemas import (
    MeetingCancel,
    MeetingComplete,
    MeetingContactSummary,
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingSearchResult,
    MeetingUpdate,
    SSEStartResponse,
)


# ====================================================================
# Excepciones de dominio
# ====================================================================


class MeetingNotFoundError(Exception):
    """Meeting no encontrado por id (o soft-deleted via cancelled)."""


class MeetingStateError(Exception):
    """Transición de status inválida (ej. complete sobre cancelled)."""


# ====================================================================
# Helpers internos
# ====================================================================


def _render_safe_html(body_markdown: str | None) -> str | None:
    """Render conservador HTML-safe del markdown (defensa profunda).

    Pattern espejo M29 ``_render_safe_html``: HTML escape + newlines
    a ``<br>``. Render real markdown rich (negritas, listas, links)
    sucede client-side via react-markdown + rehype-sanitize.

    Nota: ``notes_html_sanitized`` es fallback safe para emails out-of-band
    y previews sin frontend (e.g. PostMeetingActions email_summary).
    """
    if body_markdown is None or body_markdown == "":
        return None
    return html.escape(body_markdown).replace("\n", "<br>")


def _excerpt(body: str | None, max_chars: int = 200) -> str:
    """Trunca body al máximo de chars + ellipsis si overflow."""
    if not body:
        return ""
    if len(body) <= max_chars:
        return body
    return body[: max_chars - 1].rstrip() + "…"


async def _build_contact_summary(
    db: AsyncSession,
    contact_id: uuid.UUID,
) -> MeetingContactSummary | None:
    """Resuelve mini-card M30 si contacto existe + activo."""
    contact = await db.get(ClientContact, contact_id)
    if contact is None or contact.deleted_at is not None:
        return None
    return MeetingContactSummary(
        contact_id=contact.id,
        full_name=contact.full_name,
        role_title=contact.role_title,
        role_category=contact.role_category,
        email=contact.email,
        notes_excerpt=_excerpt(contact.notes_marcos),
    )


# ====================================================================
# Servicio
# ====================================================================


class MeetingService:
    """Servicio meetings (motor m_meetings)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ----------------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------------

    async def _bypass_rls(self) -> None:
        """SET LOCAL ROLE fulkro_app_bypassrls (admin BYPASSRLS) — pattern m12/m18 admin.

        exploratory_meetings tiene RLS ``client_isolation`` policy
        creada en M27 lifecycle migration. Admin endpoints
        (require_owner router-level) bypass via fulkro role.
        """
        await self.db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    async def create_meeting(
        self,
        payload: MeetingCreate,
    ) -> ExploratoryMeetingRow:
        """Crea meeting en estado 'scheduled'."""
        await self._bypass_rls()
        meeting = ExploratoryMeetingRow(
            client_id=payload.client_id,
            project_id=payload.project_id,
            title=payload.title,
            platform=payload.platform,
            meeting_url=payload.meeting_url,
            etapa_k=payload.etapa_k,
            interlocutor_contact_id=payload.interlocutor_contact_id,
            meeting_date=payload.scheduled_at,
            lead_source=payload.lead_source,
            status="scheduled",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(meeting)
        await self.db.flush()
        await self.db.refresh(meeting)
        return meeting

    async def list_meetings(
        self,
        *,
        client_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ExploratoryMeetingRow]:
        """Lista meetings con filtros opcionales."""
        await self._bypass_rls()
        stmt = select(ExploratoryMeetingRow)
        if client_id is not None:
            stmt = stmt.where(ExploratoryMeetingRow.client_id == client_id)
        if project_id is not None:
            stmt = stmt.where(ExploratoryMeetingRow.project_id == project_id)
        if status is not None:
            stmt = stmt.where(ExploratoryMeetingRow.status == status)
        stmt = stmt.order_by(
            desc(ExploratoryMeetingRow.meeting_date),
            desc(ExploratoryMeetingRow.created_at),
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars())

    async def get_meeting_by_id(
        self,
        meeting_id: uuid.UUID,
    ) -> ExploratoryMeetingRow:
        """Fetch single meeting o raise."""
        await self._bypass_rls()
        meeting = await self.db.get(ExploratoryMeetingRow, meeting_id)
        if meeting is None:
            raise MeetingNotFoundError(
                f"Meeting {meeting_id} no encontrado."
            )
        return meeting

    async def update_meeting(
        self,
        meeting_id: uuid.UUID,
        payload: MeetingUpdate,
    ) -> ExploratoryMeetingRow:
        """PATCH partial pre-completion. No permite update si completed/cancelled."""
        meeting = await self.get_meeting_by_id(meeting_id)
        if meeting.status in ("completed", "cancelled"):
            raise MeetingStateError(
                f"No se puede actualizar meeting en estado '{meeting.status}'."
            )

        data = payload.model_dump(exclude_unset=True)
        # Mapping schema → modelo: scheduled_at → meeting_date
        if "scheduled_at" in data:
            meeting.meeting_date = data.pop("scheduled_at")
        # Notes autosave (sub-bloque 7.B.5): re-render html_sanitized
        # cuando notes_markdown cambia.
        if "notes_markdown" in data:
            new_md = data.pop("notes_markdown")
            meeting.notes_markdown = new_md
            meeting.notes_html_sanitized = _render_safe_html(new_md)
        for key, value in data.items():
            setattr(meeting, key, value)

        await self.db.flush()
        await self.db.refresh(meeting)
        return meeting

    async def complete_meeting(
        self,
        meeting_id: uuid.UUID,
        payload: MeetingComplete,
    ) -> ExploratoryMeetingRow:
        """Completa meeting: notes + status + auto-log M30 si contact."""
        meeting = await self.get_meeting_by_id(meeting_id)
        if meeting.status == "completed":
            return meeting  # idempotente
        if meeting.status == "cancelled":
            raise MeetingStateError(
                "No se puede completar meeting cancelled."
            )

        if payload.notes_markdown is not None:
            meeting.notes_markdown = payload.notes_markdown
            meeting.notes_html_sanitized = _render_safe_html(
                payload.notes_markdown,
            )
        if payload.duration_minutes is not None:
            meeting.duration_minutes = payload.duration_minutes
        if payload.outputs_agente_18 is not None:
            meeting.outputs_agente_18_jsonb = payload.outputs_agente_18

        meeting.status = "completed"
        meeting.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(meeting)

        # Cross-motor M30: log interaction si contact presente
        if meeting.interlocutor_contact_id is not None:
            await self._log_interaction_m30(meeting)

        return meeting

    async def cancel_meeting(
        self,
        meeting_id: uuid.UUID,
        payload: MeetingCancel,
    ) -> ExploratoryMeetingRow:
        """Cancela meeting (idempotente). Persiste reason en lead_source si presente."""
        meeting = await self.get_meeting_by_id(meeting_id)
        if meeting.status == "cancelled":
            return meeting
        if meeting.status == "completed":
            raise MeetingStateError(
                "No se puede cancelar meeting completed."
            )
        meeting.status = "cancelled"
        meeting.cancelled_at = datetime.now(timezone.utc)
        if payload.reason:
            existing = meeting.lead_source or ""
            meeting.lead_source = (
                f"{existing}|cancelled:{payload.reason[:200]}"
                if existing else f"cancelled:{payload.reason[:200]}"
            )[:40]
        await self.db.flush()
        await self.db.refresh(meeting)
        return meeting

    async def soft_delete_meeting(
        self,
        meeting_id: uuid.UUID,
    ) -> None:
        """Soft-delete via cancellation (no deleted_at column en este model)."""
        await self.cancel_meeting(
            meeting_id,
            MeetingCancel(reason="admin_delete"),
        )

    # ----------------------------------------------------------------
    # Search + histórica
    # ----------------------------------------------------------------

    async def search_meetings_fts(
        self,
        query: str,
        *,
        client_id: uuid.UUID | None = None,
        limit: int = 25,
    ) -> list[MeetingSearchResult]:
        """Full-text search GIN español sobre notes_markdown."""
        if not query.strip():
            return []
        await self._bypass_rls()
        stmt = (
            select(ExploratoryMeetingRow)
            .where(
                text(
                    "to_tsvector('spanish', coalesce(notes_markdown, '')) "
                    "@@ plainto_tsquery('spanish', :q)"
                ).bindparams(q=query),
            )
            .order_by(desc(ExploratoryMeetingRow.meeting_date))
            .limit(limit)
        )
        if client_id is not None:
            stmt = stmt.where(ExploratoryMeetingRow.client_id == client_id)
        result = await self.db.execute(stmt)
        return [
            MeetingSearchResult(
                id=m.id,
                client_id=m.client_id,
                title=m.title,
                meeting_date=m.meeting_date,
                status=m.status,
                snippet=_excerpt(m.notes_markdown, 200),
            )
            for m in result.scalars()
        ]

    async def get_meetings_by_client(
        self,
        client_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[MeetingListItem]:
        """Vista histórica meetings de un cliente con interlocutor_name JOIN."""
        await self._bypass_rls()
        stmt = (
            select(
                ExploratoryMeetingRow,
                ClientContact.full_name,
            )
            .outerjoin(
                ClientContact,
                ExploratoryMeetingRow.interlocutor_contact_id
                == ClientContact.id,
            )
            .where(ExploratoryMeetingRow.client_id == client_id)
            .order_by(desc(ExploratoryMeetingRow.meeting_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items: list[MeetingListItem] = []
        for meeting, contact_name in result.all():
            items.append(
                MeetingListItem(
                    id=meeting.id,
                    client_id=meeting.client_id,
                    project_id=meeting.project_id,
                    title=meeting.title,
                    platform=meeting.platform,
                    etapa_k=meeting.etapa_k,
                    interlocutor_contact_id=meeting.interlocutor_contact_id,
                    interlocutor_name=contact_name,
                    meeting_date=meeting.meeting_date,
                    status=meeting.status,
                    duration_minutes=meeting.duration_minutes,
                    has_notes=bool(meeting.notes_markdown),
                )
            )
        return items

    # ----------------------------------------------------------------
    # SSE init
    # ----------------------------------------------------------------

    async def init_sse_session(
        self,
        meeting_id: uuid.UUID,
    ) -> SSEStartResponse:
        """Genera UUID sse_session_id + persiste en row.

        Idempotente: si ya hay sse_session_id, lo retorna.
        """
        meeting = await self.get_meeting_by_id(meeting_id)
        if meeting.sse_session_id is None:
            meeting.sse_session_id = uuid.uuid4()
            await self.db.flush()
            await self.db.refresh(meeting)
        return SSEStartResponse(
            sse_session_id=meeting.sse_session_id,
            stream_url=(
                f"/api/v1/agents/18/meeting-update/stream/"
                f"{meeting.sse_session_id}"
            ),
        )

    # ----------------------------------------------------------------
    # Detail builder
    # ----------------------------------------------------------------

    async def build_detail(
        self,
        meeting: ExploratoryMeetingRow,
    ) -> MeetingDetail:
        """Construye MeetingDetail con interlocutor mini-card resolved."""
        interlocutor: MeetingContactSummary | None = None
        if meeting.interlocutor_contact_id is not None:
            interlocutor = await _build_contact_summary(
                self.db, meeting.interlocutor_contact_id,
            )

        return MeetingDetail(
            id=meeting.id,
            client_id=meeting.client_id,
            project_id=meeting.project_id,
            title=meeting.title,
            platform=meeting.platform,
            meeting_url=meeting.meeting_url,
            etapa_k=meeting.etapa_k,
            interlocutor_contact_id=meeting.interlocutor_contact_id,
            interlocutor=interlocutor,
            meeting_date=meeting.meeting_date,
            duration_minutes=meeting.duration_minutes,
            status=meeting.status,
            completed_at=meeting.completed_at,
            cancelled_at=meeting.cancelled_at,
            notes_markdown=meeting.notes_markdown,
            notes_html_sanitized=meeting.notes_html_sanitized,
            sse_session_id=meeting.sse_session_id,
            outputs_agente_18=meeting.outputs_agente_18_jsonb,
            lead_source=meeting.lead_source,
            conversion_status=meeting.conversion_status,
            proposal_generated_id=meeting.proposal_generated_id,
            created_at=meeting.created_at,
        )

    # ----------------------------------------------------------------
    # Cross-motor M30
    # ----------------------------------------------------------------

    async def _log_interaction_m30(
        self,
        meeting: ExploratoryMeetingRow,
    ) -> None:
        """Auto-log M30 timeline al complete_meeting con contact presente.

        Silent fail si contacto no existe (pattern A18/M14/M29).
        """
        from backend.app.motors.m30_client_contacts.service import (
            ClientContactService,
            ContactNotFoundError,
        )
        if meeting.interlocutor_contact_id is None:
            return
        try:
            await ClientContactService(self.db).log_interaction(
                contact_id=meeting.interlocutor_contact_id,
                interaction_type="meeting",
                source_motor="meetings",
                source_id=meeting.id,
                summary=meeting.title or "Reunión",
                details={
                    "platform": meeting.platform,
                    "duration_minutes": meeting.duration_minutes,
                    "etapa_k": meeting.etapa_k,
                    "client_id": str(meeting.client_id),
                    "project_id": (
                        str(meeting.project_id) if meeting.project_id else None
                    ),
                },
            )
        except ContactNotFoundError:
            # contacto borrado entre creación meeting y completion — no rompe
            pass
