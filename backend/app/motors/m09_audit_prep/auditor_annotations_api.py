"""Auditor portal annotations CRUD · CLUSTER 3 Phase C1.2.

Two router groups:
1. ``router_public`` · auditor portal endpoints (token-gated · _validate_token_peek)
   - POST   /public/auditor-portal/{token}/annotations
   - GET    /public/auditor-portal/{token}/annotations
   - GET    /public/auditor-portal/{token}/annotations/{annotation_id}
   - DELETE /public/auditor-portal/{token}/annotations/{annotation_id} (24h window)

2. ``router_admin`` · admin endpoints (require_owner)
   - GET    /admin/projects/{project_id}/audit/annotations
   - PATCH  /admin/projects/{project_id}/audit/annotations/{annotation_id}

emit_auditor_event integration:
- auditor.annotation.created
- auditor.annotation.deleted (self-soft-delete window)
- admin.annotation.responded
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auditor_annotations import AuditorAnnotation
from backend.app.motors.m09_audit_prep.audit_events import (
    AUDITOR_ANNOTATION_CREATED,
    AUDITOR_ANNOTATION_DELETED,
    ADMIN_ANNOTATION_RESPONDED,
)
from backend.app.motors.m09_audit_prep.public_api import (
    _validate_token_peek,
    emit_auditor_event,
)


# ════════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════════


class AnnotationCreateRequest(BaseModel):
    target_type: str = Field(
        ...,
        description=(
            "evidence · medida · magerit_asset · magerit_threat · "
            "magerit_safeguard · plan_task · audit_log_entry"
        ),
    )
    target_id: uuid.UUID
    annotation_text: str = Field(..., min_length=1, max_length=10000)
    flag_severity: str = Field(
        ..., description="info · warning · concern · critical",
    )


class AnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    annotation_text: str
    flag_severity: str
    status: str
    admin_response: str | None
    admin_responded_at: datetime | None
    admin_responded_by: str | None
    created_at: datetime
    updated_at: datetime | None


class AnnotationListResponse(BaseModel):
    total: int
    items: list[AnnotationOut]


class AdminAnnotationPatchRequest(BaseModel):
    admin_response: str | None = Field(None, max_length=10000)
    status: str | None = Field(
        None,
        description="open · admin_reviewed · resolved · dismissed",
    )


# ════════════════════════════════════════════════════════════════════════
# Auditor portal router (token-gated)
# ════════════════════════════════════════════════════════════════════════

router_public = APIRouter(
    prefix="/public/auditor-portal",
    tags=["Public Portal · Auditor ENAC Annotations (Motor 9 · CLUSTER 3 C1)"],
)


def _validate_severity(value: str) -> str:
    if value not in AuditorAnnotation.SEVERITY_VALUES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"flag_severity inválido · valores válidos: "
                f"{sorted(AuditorAnnotation.SEVERITY_VALUES)}"
            ),
        )
    return value


def _validate_target_type(value: str) -> str:
    if value not in AuditorAnnotation.TARGET_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"target_type inválido · valores válidos: "
                f"{sorted(AuditorAnnotation.TARGET_TYPES)}"
            ),
        )
    return value


def _validate_status(value: str) -> str:
    if value not in AuditorAnnotation.STATUS_VALUES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=(
                f"status inválido · valores válidos: "
                f"{sorted(AuditorAnnotation.STATUS_VALUES)}"
            ),
        )
    return value


@router_public.post("/{token}/annotations", status_code=http_status.HTTP_201_CREATED)
async def create_annotation(
    token: str,
    body: AnnotationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Crear anotación auditor sobre target cross-motor."""
    ctx = await _validate_token_peek(token, request, db)
    _validate_target_type(body.target_type)
    _validate_severity(body.flag_severity)

    # Resolve client_id desde project (cached pattern emit_auditor_event)
    client_id_row = (await db.execute(sa_text(
        "SELECT client_id FROM projects WHERE id = :pid"
    ), {"pid": str(ctx.project_id)})).first()
    if client_id_row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    client_id = client_id_row[0]

    annotation = AuditorAnnotation(
        project_id=ctx.project_id,
        client_id=client_id,
        magic_link_id=ctx.magic_link.id,
        target_type=body.target_type,
        target_id=body.target_id,
        annotation_text=body.annotation_text,
        flag_severity=body.flag_severity,
        status="open",
    )
    db.add(annotation)
    await db.flush()

    await emit_auditor_event(
        db, ctx, AUDITOR_ANNOTATION_CREATED,
        target=body.target_type,
        metadata={
            "annotation_id": str(annotation.id),
            "target_id": str(body.target_id),
            "flag_severity": body.flag_severity,
            "text_chars": len(body.annotation_text),
        },
    )
    await db.commit()
    await db.refresh(annotation)

    return AnnotationOut.model_validate(annotation).model_dump(mode="json")


@router_public.get("/{token}/annotations", response_model=AnnotationListResponse)
async def list_annotations_auditor(
    token: str, request: Request,
    db: AsyncSession = Depends(get_db),
) -> AnnotationListResponse:
    """Lista todas las anotaciones del proyecto (NO solo creadas en esta sesión)."""
    ctx = await _validate_token_peek(token, request, db)

    stmt = (
        select(AuditorAnnotation)
        .where(AuditorAnnotation.project_id == ctx.project_id)
        .where(AuditorAnnotation.deleted_at.is_(None))
        .order_by(AuditorAnnotation.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    await db.commit()

    items = [AnnotationOut.model_validate(a) for a in rows]
    return AnnotationListResponse(total=len(items), items=items)


@router_public.get(
    "/{token}/annotations/{annotation_id}",
    response_model=AnnotationOut,
)
async def get_annotation_auditor(
    token: str,
    annotation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AnnotationOut:
    ctx = await _validate_token_peek(token, request, db)

    annotation = await db.get(AuditorAnnotation, annotation_id)
    if (
        annotation is None
        or annotation.deleted_at is not None
        or annotation.project_id != ctx.project_id
    ):
        raise HTTPException(status_code=404, detail="Annotation not found")
    await db.commit()
    return AnnotationOut.model_validate(annotation)


@router_public.delete(
    "/{token}/annotations/{annotation_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def delete_annotation_auditor(
    token: str,
    annotation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete propia · 24h window post creación · NO modificable después."""
    ctx = await _validate_token_peek(token, request, db)

    annotation = await db.get(AuditorAnnotation, annotation_id)
    if (
        annotation is None
        or annotation.deleted_at is not None
        or annotation.project_id != ctx.project_id
    ):
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Must be authored by THIS magic_link (auditor can't delete others' annotations)
    if annotation.magic_link_id != ctx.magic_link.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Cannot delete annotation authored by different auditor session",
        )

    # 24h window check
    age = datetime.now(timezone.utc) - annotation.created_at
    if age > timedelta(hours=AuditorAnnotation.DELETE_WINDOW_HOURS):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=(
                f"Delete window expired ({AuditorAnnotation.DELETE_WINDOW_HOURS}h "
                "post creation) · annotation immutable"
            ),
        )

    annotation.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_auditor_event(
        db, ctx, AUDITOR_ANNOTATION_DELETED,
        target=annotation.target_type,
        metadata={
            "annotation_id": str(annotation.id),
            "age_hours": round(age.total_seconds() / 3600, 2),
        },
    )
    await db.commit()


# ════════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════════

router_admin = APIRouter(
    prefix="/admin/projects",
    tags=["Admin · Auditor Annotations review (Motor 9 · CLUSTER 3 C1)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.get(
    "/{project_id}/audit/annotations",
    response_model=AnnotationListResponse,
)
async def list_annotations_admin(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = None,
) -> AnnotationListResponse:
    """Admin lista annotations project filtered optional por status."""
    # Admin uses fulkro role (RLS bypass · cross-project legitimate)
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    stmt = (
        select(AuditorAnnotation)
        .where(AuditorAnnotation.project_id == project_id)
        .where(AuditorAnnotation.deleted_at.is_(None))
        .order_by(AuditorAnnotation.created_at.desc())
    )
    if status_filter:
        _validate_status(status_filter)
        stmt = stmt.where(AuditorAnnotation.status == status_filter)

    rows = (await db.execute(stmt)).scalars().all()
    items = [AnnotationOut.model_validate(a) for a in rows]
    return AnnotationListResponse(total=len(items), items=items)


@router_admin.patch(
    "/{project_id}/audit/annotations/{annotation_id}",
    response_model=AnnotationOut,
)
async def patch_annotation_admin(
    project_id: uuid.UUID,
    annotation_id: uuid.UUID,
    body: AdminAnnotationPatchRequest,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
) -> AnnotationOut:
    """Admin responde + cambia status · admin_response + admin_responded_at +
    admin_responded_by registrados.

    Emite audit_log admin.annotation.responded (NO via emit_auditor_event ·
    es admin acción · usa direct audit_log INSERT con usuario=Marcos email).
    """
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    annotation = await db.get(AuditorAnnotation, annotation_id)
    if (
        annotation is None
        or annotation.deleted_at is not None
        or annotation.project_id != project_id
    ):
        raise HTTPException(status_code=404, detail="Annotation not found")

    changed_fields: list[str] = []
    if body.admin_response is not None:
        annotation.admin_response = body.admin_response
        annotation.admin_responded_at = datetime.now(timezone.utc)
        # User email derived desde require_owner User (Marcos)
        admin_email = getattr(user, "email", None) or "marcosmata@fulkro.es"
        annotation.admin_responded_by = admin_email[:255]
        changed_fields.append("admin_response")
    if body.status is not None:
        _validate_status(body.status)
        annotation.status = body.status
        changed_fields.append("status")

    if not changed_fields:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided (admin_response or status)",
        )

    annotation.updated_at = datetime.now(timezone.utc)
    await db.flush()

    # Emit admin audit_log row · NO via emit_auditor_event (auditor token NO present)
    client_id_row = (await db.execute(sa_text(
        "SELECT client_id FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    client_id_val = str(client_id_row[0]) if client_id_row else None

    import json
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'auditor_annotations', :rid, :accion, "
        ":user, :pid, :cid, :payload, now())"
    ), {
        "rid": str(annotation_id),
        "accion": ADMIN_ANNOTATION_RESPONDED,
        "user": (getattr(user, "email", None) or "marcosmata@fulkro.es")[:255],
        "pid": str(project_id),
        "cid": client_id_val,
        "payload": json.dumps({
            "annotation_id": str(annotation_id),
            "changed_fields": changed_fields,
            "new_status": annotation.status,
            "flag_severity": annotation.flag_severity,
        }),
    })
    await db.flush()
    await db.commit()
    await db.refresh(annotation)
    return AnnotationOut.model_validate(annotation)
