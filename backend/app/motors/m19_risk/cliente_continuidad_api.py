"""Cliente continuidad API · CLUSTER 2 Phase 2F.

Filosofía cliente-mínimo · cliente endpoints:
- GET  /client-portal/continuidad/questionnaire   · cliente reads own input
- POST /client-portal/continuidad/questionnaire   · cliente submits/updates input
- GET  /client-portal/continuidad/drafts          · cliente lists drafts Marcos
- POST /client-portal/continuidad/drafts/{id}/approve   · cliente APROBA binding
- POST /client-portal/continuidad/drafts/{id}/comment   · cliente solicita cambios

audit_log Sub-atom 5.A 3-way OR (project_id + client_id propagated).
ADR-013 doble pool · require_client_user · NO admin endpoints leaked.
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m19_risk.cliente_continuidad_service import (
    get_input,
    list_drafts,
    record_approval,
    upsert_input,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/client-portal/continuidad",
    tags=["Portal Cliente - Continuidad"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ProcesoCriticoItem(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=2000)


class ActivoCoreItem(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: Optional[str] = Field(None, max_length=100)


class QuestionnaireInputBody(BaseModel):
    """Cliente questionnaire input (R29 friendly)."""

    procesos_criticos: Optional[list[ProcesoCriticoItem]] = None
    rto_horas_tolerancia: Optional[int] = Field(None, ge=0, le=10000)
    rpo_horas_tolerancia: Optional[int] = Field(None, ge=0, le=10000)
    impacto_diario_eur: Optional[Decimal] = Field(None, ge=0)
    activos_core: Optional[list[ActivoCoreItem]] = None
    notas_cliente: Optional[str] = Field(None, max_length=5000)
    completed: bool = False


class QuestionnaireResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    submitted_at: str
    updated_at: str
    procesos_criticos: Optional[list[dict]] = None
    rto_horas_tolerancia: Optional[int] = None
    rpo_horas_tolerancia: Optional[int] = None
    impacto_diario_eur: Optional[str] = None
    activos_core: Optional[list[dict]] = None
    notas_cliente: Optional[str] = None
    completed: bool


class DraftItem(BaseModel):
    artifact_type: str
    draft_id: str
    summary: str
    rto_hours: Optional[int] = None
    rpo_hours: Optional[int] = None
    daily_impact_eur: Optional[str] = None


class DraftsListResponse(BaseModel):
    drafts: list[DraftItem]


class ApprovalBody(BaseModel):
    artifact_type: str = Field(..., pattern="^(bia|drp)$")
    comment_text: Optional[str] = Field(None, max_length=5000)


class CommentBody(BaseModel):
    artifact_type: str = Field(..., pattern="^(bia|drp)$")
    comment_text: str = Field(..., min_length=1, max_length=5000)


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_type: str
    draft_id: Optional[uuid.UUID] = None
    action: str
    comment_text: Optional[str] = None
    created_at: str


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _resolve_project(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[tuple[str, str]]:
    """Return (project_id, client_id) tuple cliente owns · None si missing."""
    row = (await db.execute(
        text(
            "SELECT id, client_id FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )).first()
    if row is None:
        return None
    return str(row[0]), str(row[1])


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: str,
    accion: str,
    registro_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """Sub-atom 5.A 3-way OR audit_log emit · best-effort try/except."""
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'cliente_continuidad', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": registro_id or str(uuid.uuid4()),
                "accion": accion,
                "usuario": "cliente",
                "pid": project_id,
                "cid": client_id,
                "payload": _json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log %s emit failed · pid=%s", accion, project_id)


async def _set_project_rls(
    db: AsyncSession, *, project_id: str, client_id: str,
) -> None:
    """Set RLS tenant context para project + client queries (SAN-B.MB-2.1)."""
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )


# ════════════════════════════════════════════════════════════════════
# Endpoints cliente
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/questionnaire", response_model=Optional[QuestionnaireResponse],
)
async def get_questionnaire(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente reads own questionnaire input · None si no submitted yet."""
    project_meta = await _resolve_project(db, user.client_id)
    if project_meta is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    project_id, client_id = project_meta
    await _set_project_rls(db, project_id=project_id, client_id=client_id)

    row = await get_input(db, project_id=uuid.UUID(project_id))
    if row is None:
        return None

    await _emit_audit_log(
        db,
        project_id=project_id,
        client_id=client_id,
        accion="cliente.continuidad.viewed",
        registro_id=str(row.id),
    )
    await db.commit()

    return QuestionnaireResponse(
        id=row.id,
        project_id=row.project_id,
        submitted_at=row.submitted_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        procesos_criticos=row.procesos_criticos,
        rto_horas_tolerancia=row.rto_horas_tolerancia,
        rpo_horas_tolerancia=row.rpo_horas_tolerancia,
        impacto_diario_eur=(
            str(row.impacto_diario_eur)
            if row.impacto_diario_eur is not None else None
        ),
        activos_core=row.activos_core,
        notas_cliente=row.notas_cliente,
        completed=row.completed,
    )


@router.post(
    "/questionnaire", response_model=QuestionnaireResponse, status_code=200,
)
async def post_questionnaire(
    body: QuestionnaireInputBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente submits/updates questionnaire input (upsert pattern)."""
    project_meta = await _resolve_project(db, user.client_id)
    if project_meta is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    project_id, client_id = project_meta
    await _set_project_rls(db, project_id=project_id, client_id=client_id)

    row = await upsert_input(
        db,
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        procesos_criticos=(
            [item.model_dump() for item in body.procesos_criticos]
            if body.procesos_criticos else None
        ),
        rto_horas_tolerancia=body.rto_horas_tolerancia,
        rpo_horas_tolerancia=body.rpo_horas_tolerancia,
        impacto_diario_eur=body.impacto_diario_eur,
        activos_core=(
            [item.model_dump() for item in body.activos_core]
            if body.activos_core else None
        ),
        notas_cliente=body.notas_cliente,
        completed=body.completed,
    )

    await _emit_audit_log(
        db,
        project_id=project_id,
        client_id=client_id,
        accion="cliente.continuidad.input",
        registro_id=str(row.id),
        payload={"completed": body.completed},
    )
    await db.commit()

    return QuestionnaireResponse(
        id=row.id,
        project_id=row.project_id,
        submitted_at=row.submitted_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        procesos_criticos=row.procesos_criticos,
        rto_horas_tolerancia=row.rto_horas_tolerancia,
        rpo_horas_tolerancia=row.rpo_horas_tolerancia,
        impacto_diario_eur=(
            str(row.impacto_diario_eur)
            if row.impacto_diario_eur is not None else None
        ),
        activos_core=row.activos_core,
        notas_cliente=row.notas_cliente,
        completed=row.completed,
    )


@router.get("/drafts", response_model=DraftsListResponse)
async def get_drafts(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente lists drafts Marcos preparados (BIA + DRP)."""
    project_meta = await _resolve_project(db, user.client_id)
    if project_meta is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    project_id, client_id = project_meta
    await _set_project_rls(db, project_id=project_id, client_id=client_id)

    drafts = await list_drafts(db, project_id=uuid.UUID(project_id))

    await _emit_audit_log(
        db,
        project_id=project_id,
        client_id=client_id,
        accion="cliente.continuidad.preview",
        payload={"drafts_count": len(drafts)},
    )
    await db.commit()

    return DraftsListResponse(drafts=[DraftItem(**d) for d in drafts])


@router.post(
    "/drafts/{draft_id}/approve",
    response_model=ApprovalResponse, status_code=201,
)
async def post_approve(
    draft_id: uuid.UUID,
    body: ApprovalBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente APROBA binding draft Marcos (BIA/DRP)."""
    project_meta = await _resolve_project(db, user.client_id)
    if project_meta is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    project_id, client_id = project_meta
    await _set_project_rls(db, project_id=project_id, client_id=client_id)

    row = await record_approval(
        db,
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        artifact_type=body.artifact_type,
        draft_id=draft_id,
        action="approved",
        comment_text=body.comment_text,
    )

    await _emit_audit_log(
        db,
        project_id=project_id,
        client_id=client_id,
        accion="cliente.continuidad.approve",
        registro_id=str(row.id),
        payload={
            "artifact_type": body.artifact_type,
            "draft_id": str(draft_id),
        },
    )
    await db.commit()

    return ApprovalResponse(
        id=row.id,
        artifact_type=row.artifact_type,
        draft_id=row.draft_id,
        action=row.action,
        comment_text=row.comment_text,
        created_at=row.created_at.isoformat(),
    )


@router.post(
    "/drafts/{draft_id}/comment",
    response_model=ApprovalResponse, status_code=201,
)
async def post_comment(
    draft_id: uuid.UUID,
    body: CommentBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente solicita cambios sobre draft (NO edita técnico · COMMENT)."""
    project_meta = await _resolve_project(db, user.client_id)
    if project_meta is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    project_id, client_id = project_meta
    await _set_project_rls(db, project_id=project_id, client_id=client_id)

    row = await record_approval(
        db,
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        artifact_type=body.artifact_type,
        draft_id=draft_id,
        action="comment",
        comment_text=body.comment_text,
    )

    await _emit_audit_log(
        db,
        project_id=project_id,
        client_id=client_id,
        accion="cliente.continuidad.comment",
        registro_id=str(row.id),
        payload={
            "artifact_type": body.artifact_type,
            "draft_id": str(draft_id),
        },
    )
    await db.commit()

    return ApprovalResponse(
        id=row.id,
        artifact_type=row.artifact_type,
        draft_id=row.draft_id,
        action=row.action,
        comment_text=row.comment_text,
        created_at=row.created_at.isoformat(),
    )
