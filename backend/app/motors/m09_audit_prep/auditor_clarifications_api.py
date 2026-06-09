"""Auditor portal clarifications CRUD · CLUSTER 3 Phase C2.

Two router groups (mirror Phase C1 pattern):
1. ``router_public`` · auditor portal endpoints (token-gated)
   - POST   /public/auditor-portal/{token}/clarifications
   - GET    /public/auditor-portal/{token}/clarifications
   - GET    /public/auditor-portal/{token}/clarifications/{clarification_id}

2. ``router_admin`` · admin endpoints (require_owner)
   - GET    /admin/projects/{project_id}/audit/clarifications
   - PATCH  /admin/projects/{project_id}/audit/clarifications/{clarification_id}

Integration:
- SSE: sse_dispatcher.dispatch on channel `project:{id}` emits
  ``auditor_clarification_new`` (admin subscribers receive realtime)
- Email backup: EmailSender (best-effort · NO bloquea primary persist) ·
  template notify_admin_clarification_received
- audit_log: emit_auditor_event canonical events (Phase 6 helper reused)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.config import get_settings
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db
from backend.app.models.auditor_clarifications import AuditorClarificationRequest
from backend.app.motors.m09_audit_prep.audit_events import (
    ADMIN_CLARIFICATION_RESPONDED,
    AUDITOR_CLARIFICATION_REQUESTED,
)
from backend.app.motors.m09_audit_prep.public_api import (
    _validate_token_peek,
    emit_auditor_event,
)


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════════


class ClarificationCreateRequest(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=10000)
    linked_target_type: str = Field(default="general")
    linked_target_id: uuid.UUID | None = None
    priority: str = Field(default="normal")


class ClarificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    question_text: str
    linked_target_type: str
    linked_target_id: uuid.UUID | None
    priority: str
    status: str
    admin_response: str | None
    admin_responded_at: datetime | None
    admin_responded_by: str | None
    created_at: datetime
    updated_at: datetime | None


class ClarificationListResponse(BaseModel):
    total: int
    items: list[ClarificationOut]


class AdminClarificationPatchRequest(BaseModel):
    admin_response: str | None = Field(None, max_length=10000)
    status: str | None = Field(
        None, description="open · in_progress · responded · closed",
    )


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════


def _validate_target_type(value: str) -> str:
    if value not in AuditorClarificationRequest.TARGET_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"linked_target_type inválido · valores válidos: "
                f"{sorted(AuditorClarificationRequest.TARGET_TYPES)}"
            ),
        )
    return value


def _validate_priority(value: str) -> str:
    if value not in AuditorClarificationRequest.PRIORITY_VALUES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"priority inválida · valores válidos: "
                f"{sorted(AuditorClarificationRequest.PRIORITY_VALUES)}"
            ),
        )
    return value


def _validate_status(value: str) -> str:
    if value not in AuditorClarificationRequest.STATUS_VALUES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"status inválido · valores válidos: "
                f"{sorted(AuditorClarificationRequest.STATUS_VALUES)}"
            ),
        )
    return value


async def _notify_admin_email_best_effort(
    db: AsyncSession,
    *,
    clarification: AuditorClarificationRequest,
    auditor_email: str,
    project_name: str,
) -> None:
    """Best-effort email notification to Marcos. NO bloquea primary persist.

    Pattern notify_best_effort (Bloque 3+5) · try/except logger.exception +
    graceful degradation. NOT awaited critical path · si SMTP cae, request
    sigue completándose (SSE dispatch primary signal).
    """
    try:
        from backend.app.core.email.sender import get_email_sender

        settings = get_settings()
        admin_email = settings.marcos_admin_email
        sender = get_email_sender()

        priority_label = clarification.priority.upper()
        subject = (
            f"[Portal auditor · {priority_label}] Aclaración solicitada · "
            f"{project_name}"
        )
        html_body = (
            f"<p><strong>Auditor:</strong> {auditor_email}</p>"
            f"<p><strong>Proyecto:</strong> {project_name}</p>"
            f"<p><strong>Prioridad:</strong> {clarification.priority}</p>"
            f"<p><strong>Anclaje:</strong> {clarification.linked_target_type}"
            + (
                f" ({clarification.linked_target_id})"
                if clarification.linked_target_id else ""
            )
            + "</p>"
            f"<hr/>"
            f"<p><strong>Pregunta:</strong></p>"
            f"<blockquote style='border-left:3px solid #6c63ff; "
            f"padding-left:12px; color:#444;'>{clarification.question_text}"
            f"</blockquote>"
            f"<p><a href='https://fulkro.local/admin/projects/"
            f"{clarification.project_id}/audit/clarifications'>"
            f"Responder en el portal admin</a></p>"
        )
        await sender.send(
            db,
            to=admin_email,
            subject=subject,
            html_body=html_body,
            template_used="notify_admin_clarification_received",
            client_id=clarification.client_id,
            metadata={
                "clarification_id": str(clarification.id),
                "project_id": str(clarification.project_id),
                "priority": clarification.priority,
            },
        )
    except Exception:
        logger.exception(
            "Auditor clarification email notification failed (best-effort) · "
            "clarification_id=%s",
            clarification.id,
        )


# ════════════════════════════════════════════════════════════════════════
# Auditor portal router (token-gated)
# ════════════════════════════════════════════════════════════════════════

router_public = APIRouter(
    prefix="/public/auditor-portal",
    tags=["Public Portal · Auditor ENAC Clarifications (Motor 9 · CLUSTER 3 C2)"],
)


@router_public.post(
    "/{token}/clarifications", status_code=http_status.HTTP_201_CREATED,
)
async def create_clarification(
    token: str,
    body: ClarificationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Auditor crea solicitud de aclaración · admin notificado via SSE + email."""
    ctx = await _validate_token_peek(token, request, db)
    _validate_target_type(body.linked_target_type)
    _validate_priority(body.priority)
    if body.linked_target_type == "general" and body.linked_target_id is not None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="linked_target_id debe ser NULL cuando linked_target_type='general'",
        )

    project_row = (await db.execute(sa_text(
        "SELECT client_id, nombre FROM projects WHERE id = :pid"
    ), {"pid": str(ctx.project_id)})).first()
    if project_row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    clarification = AuditorClarificationRequest(
        project_id=ctx.project_id,
        client_id=project_row[0],
        magic_link_id=ctx.magic_link.id,
        question_text=body.question_text,
        linked_target_type=body.linked_target_type,
        linked_target_id=body.linked_target_id,
        priority=body.priority,
        status="open",
    )
    db.add(clarification)
    await db.flush()

    auditor_email = (
        ctx.magic_link.recipient_email
        or (ctx.scope or {}).get("auditor_email")
        or "auditor"
    )

    await emit_auditor_event(
        db, ctx, AUDITOR_CLARIFICATION_REQUESTED,
        target=body.linked_target_type,
        metadata={
            "clarification_id": str(clarification.id),
            "priority": body.priority,
            "linked_target_id": (
                str(body.linked_target_id) if body.linked_target_id else None
            ),
            "question_chars": len(body.question_text),
        },
    )

    # Best-effort email backup (NO bloquea primary)
    await _notify_admin_email_best_effort(
        db,
        clarification=clarification,
        auditor_email=auditor_email,
        project_name=project_row[1] or "Proyecto",
    )

    await db.commit()
    await db.refresh(clarification)

    # SSE realtime notification para admin subscribers project channel
    # NO bloquea response · best-effort
    try:
        await sse_dispatcher.dispatch(
            f"project:{ctx.project_id}",
            "auditor_clarification_new",
            {
                "clarification_id": str(clarification.id),
                "priority": clarification.priority,
                "linked_target_type": clarification.linked_target_type,
                "preview": body.question_text[:120],
                "auditor_email": auditor_email,
            },
        )
    except Exception:
        logger.exception(
            "SSE dispatch failed for clarification %s (best-effort)",
            clarification.id,
        )

    return ClarificationOut.model_validate(clarification).model_dump(mode="json")


@router_public.get(
    "/{token}/clarifications", response_model=ClarificationListResponse,
)
async def list_clarifications_auditor(
    token: str, request: Request,
    db: AsyncSession = Depends(get_db),
) -> ClarificationListResponse:
    """Auditor lista clarifications del proyecto (NO solo de esta sesión)."""
    ctx = await _validate_token_peek(token, request, db)

    stmt = (
        select(AuditorClarificationRequest)
        .where(AuditorClarificationRequest.project_id == ctx.project_id)
        .where(AuditorClarificationRequest.deleted_at.is_(None))
        .order_by(AuditorClarificationRequest.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    await db.commit()

    items = [ClarificationOut.model_validate(c) for c in rows]
    return ClarificationListResponse(total=len(items), items=items)


@router_public.get(
    "/{token}/clarifications/{clarification_id}",
    response_model=ClarificationOut,
)
async def get_clarification_auditor(
    token: str,
    clarification_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ClarificationOut:
    ctx = await _validate_token_peek(token, request, db)

    clarification = await db.get(AuditorClarificationRequest, clarification_id)
    if (
        clarification is None
        or clarification.deleted_at is not None
        or clarification.project_id != ctx.project_id
    ):
        raise HTTPException(status_code=404, detail="Clarification not found")
    await db.commit()
    return ClarificationOut.model_validate(clarification)


# ════════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════════

router_admin = APIRouter(
    prefix="/admin/projects",
    tags=["Admin · Auditor Clarifications (Motor 9 · CLUSTER 3 C2)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.get(
    "/{project_id}/audit/clarifications",
    response_model=ClarificationListResponse,
)
async def list_clarifications_admin(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = None,
    priority_filter: str | None = None,
) -> ClarificationListResponse:
    """Admin lista clarifications · filter optional status + priority."""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    stmt = (
        select(AuditorClarificationRequest)
        .where(AuditorClarificationRequest.project_id == project_id)
        .where(AuditorClarificationRequest.deleted_at.is_(None))
        .order_by(AuditorClarificationRequest.created_at.desc())
    )
    if status_filter:
        _validate_status(status_filter)
        stmt = stmt.where(AuditorClarificationRequest.status == status_filter)
    if priority_filter:
        _validate_priority(priority_filter)
        stmt = stmt.where(
            AuditorClarificationRequest.priority == priority_filter,
        )

    rows = (await db.execute(stmt)).scalars().all()
    items = [ClarificationOut.model_validate(c) for c in rows]
    return ClarificationListResponse(total=len(items), items=items)


@router_admin.patch(
    "/{project_id}/audit/clarifications/{clarification_id}",
    response_model=ClarificationOut,
)
async def patch_clarification_admin(
    project_id: uuid.UUID,
    clarification_id: uuid.UUID,
    body: AdminClarificationPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
) -> ClarificationOut:
    """Admin responde + cambia status · emit canonical event admin.*"""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    clarification = await db.get(AuditorClarificationRequest, clarification_id)
    if (
        clarification is None
        or clarification.deleted_at is not None
        or clarification.project_id != project_id
    ):
        raise HTTPException(status_code=404, detail="Clarification not found")

    changed_fields: list[str] = []
    if body.admin_response is not None:
        clarification.admin_response = body.admin_response
        clarification.admin_responded_at = datetime.now(timezone.utc)
        admin_email = getattr(user, "email", None) or "marcosmata@fulkro.es"
        clarification.admin_responded_by = admin_email[:255]
        # If admin responds + status NOT yet set explicit, auto-advance
        if body.status is None and clarification.status in (
            "open", "in_progress",
        ):
            clarification.status = "responded"
        changed_fields.append("admin_response")
    if body.status is not None:
        _validate_status(body.status)
        clarification.status = body.status
        if "status" not in changed_fields:
            changed_fields.append("status")

    if not changed_fields:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided (admin_response or status)",
        )

    clarification.updated_at = datetime.now(timezone.utc)
    await db.flush()

    # Emit admin audit_log row (direct · NO via emit_auditor_event)
    client_id_row = (await db.execute(sa_text(
        "SELECT client_id FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    client_id_val = str(client_id_row[0]) if client_id_row else None

    import json
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'auditor_clarifications', :rid, :accion, "
        ":user, :pid, :cid, :payload, now())"
    ), {
        "rid": str(clarification_id),
        "accion": ADMIN_CLARIFICATION_RESPONDED,
        "user": (getattr(user, "email", None) or "marcosmata@fulkro.es")[:255],
        "pid": str(project_id),
        "cid": client_id_val,
        "payload": json.dumps({
            "clarification_id": str(clarification_id),
            "changed_fields": changed_fields,
            "new_status": clarification.status,
            "priority": clarification.priority,
        }),
    })
    await db.flush()
    await db.commit()
    await db.refresh(clarification)
    return ClarificationOut.model_validate(clarification)
