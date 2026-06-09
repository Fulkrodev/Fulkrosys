"""PostMeetingActions dispatcher (sub-bloque 7.A.6 wiring real).

4 acciones cross-motor invocadas desde POST /admin/meetings/{id}/post-action:
  - propuesta → A19 RedactorPropuestasAgent → P-001 DOCX draft
  - create_project → ORM Project insert + scheduling
  - k6_signature → M12 magic link FIRMA_DOCUMENTO con M30 contact
  - email_summary → EmailSender consolidado con render meeting

Decisiones audit-first:
  - A19 generate_proposal requiere project_id existing — orquestación:
    cliente puede llamar create_project → propuesta secuencial.
  - email_summary destinatario: contact.email si interlocutor, sino
    fallback admin_settings o explicit payload['to_email'].
  - Toda acción registra meeting.proposal_generated_id si A19 success.
"""
from __future__ import annotations

import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.conformity_lifecycle import ExploratoryMeetingRow
from backend.app.motors.m_meetings.schemas import (
    MeetingPostActionRequest,
    MeetingPostActionResponse,
    PostActionType,
)


logger = logging.getLogger(__name__)


_HandlerFn = Callable[
    [AsyncSession, ExploratoryMeetingRow, MeetingPostActionRequest],
    Awaitable[MeetingPostActionResponse],
]


async def dispatch_post_action(
    db: AsyncSession,
    meeting: ExploratoryMeetingRow,
    payload: MeetingPostActionRequest,
) -> MeetingPostActionResponse:
    """Dispatch action por type."""
    handlers: dict[PostActionType, _HandlerFn] = {
        "propuesta": _action_propuesta,
        "create_project": _action_create_project,
        "k6_signature": _action_k6_signature,
        "email_summary": _action_email_summary,
    }
    handler = handlers.get(payload.action_type)
    if handler is None:
        return MeetingPostActionResponse(
            action_type=payload.action_type,
            success=False,
            error_message=(
                f"Unknown action_type '{payload.action_type}'. "
                f"Allowed: {list(handlers.keys())}."
            ),
        )
    try:
        return await handler(db, meeting, payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "PostMeetingAction %s failed for meeting %s",
            payload.action_type, meeting.id,
        )
        return MeetingPostActionResponse(
            action_type=payload.action_type,
            success=False,
            error_message=f"{type(exc).__name__}: {exc}",
        )


# ────────────────────────────────────────────────────────────────────
# Action 1: propuesta — A19 RedactorPropuestasAgent
# ────────────────────────────────────────────────────────────────────


async def _action_propuesta(
    db: AsyncSession,
    meeting: ExploratoryMeetingRow,
    payload: MeetingPostActionRequest,
) -> MeetingPostActionResponse:
    """Genera P-001 draft con A19 sobre project_id meeting.

    Requiere ``meeting.project_id`` populated. Si meeting es lead
    pre-proyecto, llamar create_project antes (frontend orchestration).

    Payload opcional: overrides para A19 generate_proposal kwargs.
    """
    if meeting.project_id is None:
        return MeetingPostActionResponse(
            action_type="propuesta",
            success=False,
            error_message=(
                "Meeting sin project_id asignado. Ejecuta primero "
                "action_type='create_project' o asigna project en update."
            ),
        )

    from backend.app.agents.agent_19_propuestas import (
        RedactorPropuestasAgent,
    )

    agent = RedactorPropuestasAgent()
    overrides = payload.payload or {}
    result = await agent.generate_proposal(
        db,
        project_id=meeting.project_id,
        sistemas_en_alcance=overrides.get("sistemas_en_alcance"),
        sedes=overrides.get("sedes"),
        madurez_pct=overrides.get("madurez_pct"),
        dias_hasta_plazo=overrides.get("dias_hasta_plazo"),
        sector_override=overrides.get("sector_override"),
        categoria_override=overrides.get("categoria_override"),
        retainer_tier=overrides.get("retainer_tier"),
    )

    # Persistir proposal_id en meeting si A19 devuelve uno
    proposal_id_raw = result.get("proposal_id") or result.get("draft_id")
    if proposal_id_raw:
        try:
            meeting.proposal_generated_id = uuid.UUID(str(proposal_id_raw))
            await db.flush()
        except (ValueError, TypeError):
            logger.warning(
                "A19 returned proposal_id not UUID-coercible: %r",
                proposal_id_raw,
            )

    return MeetingPostActionResponse(
        action_type="propuesta",
        success=True,
        result={
            "project_id": str(meeting.project_id),
            "proposal_id": (
                str(meeting.proposal_generated_id)
                if meeting.proposal_generated_id else None
            ),
            "tokens_input": result.get("tokens_input"),
            "tokens_output": result.get("tokens_output"),
            "cost_eur_estimated": result.get("cost_eur_estimated"),
            "latency_ms": result.get("latency_ms"),
            "validation": result.get("validation"),
        },
    )


# ────────────────────────────────────────────────────────────────────
# Action 2: create_project — ORM Project insert
# ────────────────────────────────────────────────────────────────────


async def _action_create_project(
    db: AsyncSession,
    meeting: ExploratoryMeetingRow,
    payload: MeetingPostActionRequest,
) -> MeetingPostActionResponse:
    """Crea Project asociado al cliente del meeting + persiste FK en meeting.

    Payload requerido:
      - nombre (str): nombre del proyecto.
    Payload opcional:
      - categoria_objetivo (str): BASICA/MEDIA/ALTA
      - fase (str): fase inicial
      - tamano_empleados (str): micro/pequeno/mediano/grande/enterprise (1.C.D.A.0.3)
      - geografia_operacion (str): spain/ue/global/apac/latam (1.C.D.A.0.3)
      - urgencia_certificacion (str): no_urge/6m/3m/1m/urgent_30d (1.C.D.A.0.3)
      - presupuesto_disponible (str): minimo/estandar/generoso/premium (1.C.D.A.0.3)
    """
    from backend.app.database import set_tenant_context
    from backend.app.models.core import Project

    data = payload.payload or {}
    nombre = data.get("nombre") or meeting.title
    if not nombre:
        return MeetingPostActionResponse(
            action_type="create_project",
            success=False,
            error_message="Payload requiere 'nombre' o meeting.title.",
        )

    if meeting.project_id is not None:
        return MeetingPostActionResponse(
            action_type="create_project",
            success=False,
            error_message=(
                f"Meeting ya tiene project_id asignado "
                f"({meeting.project_id})."
            ),
        )

    await set_tenant_context(db, client_id=meeting.client_id)
    # Sub-atom 1.C.D.A.0.3 v3.8 · captura dims pre-venta natural en reunión
    # exploratoria. Defaults sensatos via server_default si NO provided · admin
    # page consolidada permite refinar después (OPS-029 caso 9 sostenido).
    project_kwargs = {
        "client_id": meeting.client_id,
        "nombre": nombre,
        "categoria_objetivo": data.get("categoria_objetivo"),
        "fase": data.get("fase"),
    }
    # Dims pre-venta opcionales · sólo settear si provided (server_default cubre resto)
    for dim_key in (
        "tamano_empleados",
        "geografia_operacion",
        "urgencia_certificacion",
        "presupuesto_disponible",
    ):
        if data.get(dim_key) is not None:
            project_kwargs[dim_key] = data[dim_key]
    project = Project(**project_kwargs)
    db.add(project)
    await db.flush()
    await db.refresh(project)

    # Vincular meeting al nuevo project
    meeting.project_id = project.id
    await db.flush()

    return MeetingPostActionResponse(
        action_type="create_project",
        success=True,
        result={
            "project_id": str(project.id),
            "nombre": project.nombre,
            "categoria_objetivo": project.categoria_objetivo,
            "fase": project.fase,
            "tamano_empleados": project.tamano_empleados,
            "urgencia_certificacion": project.urgencia_certificacion,
            "client_id": str(meeting.client_id),
            "meeting_linked": True,
        },
    )


# ────────────────────────────────────────────────────────────────────
# Action 3: k6_signature — M12 magic link FIRMA_DOCUMENTO
# ────────────────────────────────────────────────────────────────────


async def _action_k6_signature(
    db: AsyncSession,
    meeting: ExploratoryMeetingRow,
    payload: MeetingPostActionRequest,
) -> MeetingPostActionResponse:
    """Genera magic link FIRMA_DOCUMENTO K.6 sobre proyecto del meeting.

    Payload requerido (al menos uno):
      - signatory_contact_id (UUID): contacto M30 destinatario
      - recipient_email (str): email plano si no hay contacto registrado

    Si signatory_contact_id no se pasa pero meeting.interlocutor_contact_id
    presente, usa ese (default sensato).
    """
    from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
    from backend.app.motors.m12_magic_link.schemas import (
        MagicLinkGenerateRequest,
    )
    from backend.app.motors.m12_magic_link.service import MagicLinkService
    from backend.app.config import get_settings

    if meeting.project_id is None:
        return MeetingPostActionResponse(
            action_type="k6_signature",
            success=False,
            error_message=(
                "Meeting sin project_id. Ejecuta create_project primero."
            ),
        )

    data = payload.payload or {}
    signatory_id_raw = data.get("signatory_contact_id")
    contact_id: uuid.UUID | None = None
    if signatory_id_raw:
        contact_id = uuid.UUID(str(signatory_id_raw))
    elif meeting.interlocutor_contact_id is not None:
        contact_id = meeting.interlocutor_contact_id

    recipient_email = data.get("recipient_email")
    if not recipient_email:
        # Fallback: lookup contact email si contact_id presente
        if contact_id is not None:
            from backend.app.motors.m30_client_contacts.models import (
                ClientContact,
            )
            contact = await db.get(ClientContact, contact_id)
            if contact and contact.email:
                recipient_email = contact.email
    if not recipient_email:
        return MeetingPostActionResponse(
            action_type="k6_signature",
            success=False,
            error_message=(
                "Payload requiere 'recipient_email' o "
                "signatory_contact_id (o meeting.interlocutor_contact_id) "
                "con email asociado."
            ),
        )

    settings = get_settings()
    svc = MagicLinkService(db)
    response = await svc.generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=meeting.project_id,
            purpose=MagicLinkPurpose.FIRMA_DOCUMENTO,
            recipient_email=recipient_email,
            scope={
                "meeting_id": str(meeting.id),
                "etapa_k": meeting.etapa_k,
                "title": meeting.title,
            },
            sent_to_contact_id=contact_id,
        ),
        base_url=settings.app_base_url,
    )

    return MeetingPostActionResponse(
        action_type="k6_signature",
        success=True,
        result={
            "magic_link_id": str(response.magic_link_id),
            "url": response.url,
            "otp": response.otp,  # mostrar 1 vez al admin
            "expires_at": response.expires_at.isoformat(),
            "purpose": response.purpose.value,
            "recipient_email": recipient_email,
            "sent_to_contact_id": str(contact_id) if contact_id else None,
        },
    )


# ────────────────────────────────────────────────────────────────────
# Action 4: email_summary — EmailSender consolidado
# ────────────────────────────────────────────────────────────────────


async def _action_email_summary(
    db: AsyncSession,
    meeting: ExploratoryMeetingRow,
    payload: MeetingPostActionRequest,
) -> MeetingPostActionResponse:
    """Envía resumen meeting al destinatario.

    Payload opcional:
      - to_email (str): email destinatario explícito
      - subject (str): override subject default
      - extra_message (str): mensaje libre Marcos extra al template

    Resolución destinatario (orden):
      1. payload.to_email
      2. interlocutor_contact_id.email (M30)
      3. error: requerido destinatario
    """
    from backend.app.core.email.sender import get_email_sender

    data = payload.payload or {}
    to_email = data.get("to_email")
    if not to_email and meeting.interlocutor_contact_id is not None:
        from backend.app.motors.m30_client_contacts.models import (
            ClientContact,
        )
        contact = await db.get(ClientContact, meeting.interlocutor_contact_id)
        if contact and contact.email and not contact.deleted_at:
            to_email = str(contact.email)

    if not to_email:
        return MeetingPostActionResponse(
            action_type="email_summary",
            success=False,
            error_message=(
                "Payload requiere 'to_email' o meeting con interlocutor "
                "M30 con email asociado."
            ),
        )

    subject = data.get("subject") or (
        f"[FULKRO] Resumen reunión: {meeting.title or 'sin título'}"
    )
    extra_message = data.get("extra_message", "")
    html_body, text_body = _render_meeting_summary(meeting, extra_message)

    sender = get_email_sender()
    result = await sender.send(
        db,
        to=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        template_used="meeting_summary",
        client_id=meeting.client_id,
        metadata={
            "motor": "meetings",
            "meeting_id": str(meeting.id),
            "etapa_k": meeting.etapa_k,
        },
    )

    return MeetingPostActionResponse(
        action_type="email_summary",
        success=result.ok,
        result={
            "message_id": result.message_id,
            "backend_used": result.backend_used,
            "retry_count": result.retry_count,
            "to": to_email,
            "email_log_id": (
                str(result.email_log_id) if result.email_log_id else None
            ),
        },
        error_message=result.error if not result.ok else None,
    )


# ────────────────────────────────────────────────────────────────────
# Helpers — render summary email
# ────────────────────────────────────────────────────────────────────


def _render_meeting_summary(
    meeting: ExploratoryMeetingRow,
    extra_message: str,
) -> tuple[str, str]:
    """Render minimal HTML+text summary (template completo diferido)."""
    import html as html_lib

    title = html_lib.escape(meeting.title or "Reunión exploratoria")
    platform = html_lib.escape(meeting.platform or "—")
    etapa_k = html_lib.escape(meeting.etapa_k or "—")
    duration = (
        f"{meeting.duration_minutes} min"
        if meeting.duration_minutes else "—"
    )
    when = (
        meeting.meeting_date.strftime("%Y-%m-%d %H:%M")
        if meeting.meeting_date else "—"
    )
    notes_html = meeting.notes_html_sanitized or html_lib.escape(
        meeting.notes_markdown or "(sin notas)"
    ).replace("\n", "<br>")
    extra_html = (
        f"<p><strong>Mensaje:</strong> {html_lib.escape(extra_message)}</p>"
        if extra_message else ""
    )

    html_body = f"""<!DOCTYPE html>
<html lang="es"><body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #1a1a1a;">
  <h2 style="color: #2563eb;">Resumen de reunión FULKRO</h2>
  <p><strong>Título:</strong> {title}</p>
  <p><strong>Plataforma:</strong> {platform} · <strong>Etapa:</strong> {etapa_k} · <strong>Duración:</strong> {duration}</p>
  <p><strong>Fecha:</strong> {when}</p>
  {extra_html}
  <hr style="border: 1px solid #e5e7eb;">
  <h3 style="color: #2563eb;">Notas</h3>
  <div style="background: #f9fafb; padding: 16px; border-radius: 8px;">
    {notes_html}
  </div>
  <hr style="border: 1px solid #e5e7eb;">
  <p style="color: #6b7280; font-size: 12px;">
    Resumen automático FULKRO — Motor Meetings (FASE 7).
  </p>
</body></html>"""

    text_body = (
        f"Resumen reunión FULKRO\n\n"
        f"Título: {meeting.title or 'sin título'}\n"
        f"Plataforma: {meeting.platform or '—'}\n"
        f"Etapa: {meeting.etapa_k or '—'}\n"
        f"Duración: {duration}\n"
        f"Fecha: {when}\n\n"
        f"{extra_message + chr(10) + chr(10) if extra_message else ''}"
        f"Notas:\n{meeting.notes_markdown or '(sin notas)'}\n"
    )
    return html_body, text_body
