"""Evidence Request API · CLUSTER 3 Phase 3A workflow endpoints.

Filosofía cliente-mínimo:
- Admin endpoints (require_owner · ADR-013): create + list + detail + approve +
  reject + cancel · admin OWNS workflow
- Cliente endpoints (require_client_user · ADR-013 doble pool): list pending
  tasks · view detail R29 friendly · upload (auto-link Evidence) · mark-na
  con motivo amigable

audit_log Sub-atom 5.A 3-way OR (project_id + client_id propagated) cross
all state transitions · ENAC trazabilidad cumulative.

ClientNotification + SSE wire reuse Phase 2D DRY central function:
- Admin create → cliente recibe notif realtime + appears en pending tasks
- Admin approve/reject → cliente recibe status update realtime + motivo si reject
- Pattern #14 SSE + ClientNotification dual emit independent
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m07_evidence.request_service import (
    WorkflowStateError,
    admin_approve,
    admin_cancel,
    admin_reject,
    cliente_mark_na,
    cliente_upload,
    create_request,
    get_request,
    list_requests,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.notification_service import (
    emit_client_notification,
)


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class EvidenceRequestCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=5000)
    measure_code: Optional[str] = Field(None, max_length=40)
    control_id: Optional[uuid.UUID] = None
    tipo_documento: Optional[str] = Field(None, max_length=100)
    plantilla_url: Optional[str] = Field(None, max_length=500)
    deadline_date: Optional[date] = None
    client_user_id: Optional[uuid.UUID] = None


class EvidenceRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    client_user_id: Optional[uuid.UUID] = None
    measure_code: Optional[str] = None
    control_id: Optional[uuid.UUID] = None
    tipo_documento: Optional[str] = None
    titulo: str
    descripcion: Optional[str] = None
    plantilla_url: Optional[str] = None
    deadline_date: Optional[date] = None
    status: str
    created_by_user_id: uuid.UUID
    created_at: str
    updated_at: str
    cliente_uploaded_at: Optional[str] = None
    evidence_id: Optional[uuid.UUID] = None
    cliente_na_motivo: Optional[str] = None
    admin_validated_at: Optional[str] = None
    admin_validated_by_user_id: Optional[uuid.UUID] = None
    admin_rejection_motivo: Optional[str] = None


class EvidenceRequestList(BaseModel):
    requests: list[EvidenceRequestResponse]


class RejectBody(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=5000)


class MarkNaBody(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=5000)


class UploadLinkBody(BaseModel):
    evidence_id: uuid.UUID


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _to_response(row) -> EvidenceRequestResponse:
    return EvidenceRequestResponse(
        id=row.id,
        project_id=row.project_id,
        client_user_id=row.client_user_id,
        measure_code=row.measure_code,
        control_id=row.control_id,
        tipo_documento=row.tipo_documento,
        titulo=row.titulo,
        descripcion=row.descripcion,
        plantilla_url=row.plantilla_url,
        deadline_date=row.deadline_date,
        status=row.status,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        cliente_uploaded_at=(
            row.cliente_uploaded_at.isoformat()
            if row.cliente_uploaded_at else None
        ),
        evidence_id=row.evidence_id,
        cliente_na_motivo=row.cliente_na_motivo,
        admin_validated_at=(
            row.admin_validated_at.isoformat()
            if row.admin_validated_at else None
        ),
        admin_validated_by_user_id=row.admin_validated_by_user_id,
        admin_rejection_motivo=row.admin_rejection_motivo,
    )


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: Optional[str],
    accion: str,
    registro_id: str,
    payload: Optional[dict] = None,
    usuario: str = "system",
) -> None:
    """Sub-atom 5.A 3-way OR audit_log emit · best-effort try/except."""
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'evidence_requests', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": registro_id,
                "accion": accion,
                "usuario": usuario[:255],
                "pid": project_id,
                "cid": client_id,
                "payload": _json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log %s emit failed · rid=%s", accion, registro_id)


async def _resolve_client_id_from_project(
    db: AsyncSession, project_id: str,
) -> Optional[str]:
    """Resolve client_id from project_id (Sub-atom 5.A coherence)."""
    row = (await db.execute(
        text(
            "SELECT client_id FROM projects "
            "WHERE id = :pid AND deleted_at IS NULL"
        ),
        {"pid": project_id},
    )).first()
    return str(row[0]) if row else None


async def _set_admin_rls(
    db: AsyncSession, project_id: str,
) -> None:
    """Admin path · SET LOCAL ROLE fulkro_app_bypassrls (bypass RLS · fulkro superuser)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )


async def _set_cliente_rls(
    db: AsyncSession, *, project_id: str, client_id: str,
) -> None:
    """Cliente path · fulkro_app + tenant context propagated."""
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )


async def _resolve_cliente_project(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[tuple[str, str]]:
    """Find active project for cliente · returns (project_id, client_id)."""
    row = (await db.execute(
        text(
            "SELECT id, client_id FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )).first()
    return (str(row[0]), str(row[1])) if row else None


async def _notify_cliente_request_created(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    request_titulo: str,
    request_id: uuid.UUID,
    measure_code: Optional[str],
) -> None:
    """Emit ClientNotification cuando admin crea request (Phase 2D DRY wire).

    Best-effort: si NO active cliente users · graceful skip · primary persist
    NUNCA bloqueado.
    """
    try:
        users_rows = (await db.execute(
            text(
                "SELECT cu.id FROM client_users cu "
                "JOIN projects p ON p.client_id = cu.client_id "
                "WHERE p.id = :pid AND cu.deactivated_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).fetchall()

        for user_row in users_rows:
            await emit_client_notification(
                db=db,
                project_id=project_id,
                client_user_id=user_row[0],
                type="evidence_request",
                title=f"Aportar evidencia: {request_titulo}",
                body=(
                    f"Marcos te pide aportar un documento"
                    + (f" para la medida {measure_code}" if measure_code else "")
                    + ". Cuando puedas, sube el archivo desde tu panel · sin prisa."
                ),
                target_url=f"/client-portal/evidencias?request={request_id}",
                priority="normal",
                emitted_by_motor="m07_evidence_request",
                payload={
                    "request_id": str(request_id),
                    "measure_code": measure_code,
                },
            )
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "ClientNotification emit failed · request_id=%s", request_id,
        )


async def _notify_cliente_status_update(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: Optional[uuid.UUID],
    request_titulo: str,
    request_id: uuid.UUID,
    new_status: str,
    motivo: Optional[str] = None,
) -> None:
    """Emit ClientNotification cuando admin approve/reject (Phase 2D DRY).

    R29 firmísimo · friendly Spanish · motivo claro si rejected.
    """
    if not client_user_id:
        return
    try:
        if new_status == "approved":
            title = f"Evidencia aceptada: {request_titulo}"
            body = (
                "Marcos validó la evidencia que enviaste. ¡Gracias por la rapidez!"
            )
            priority = "normal"
        elif new_status == "rejected":
            title = f"Necesitamos otra versión: {request_titulo}"
            motivo_text = motivo or "Marcos pide cambios"
            body = (
                f"{motivo_text}\n\nCuando puedas vuelve al panel y sube una "
                "nueva versión · sin prisa."
            )
            priority = "high"
        else:
            return  # otros status NO notify cliente

        await emit_client_notification(
            db=db,
            project_id=project_id,
            client_user_id=client_user_id,
            type="evidence_request",
            title=title,
            body=body,
            target_url=f"/client-portal/evidencias?request={request_id}",
            priority=priority,
            emitted_by_motor="m07_evidence_request",
            payload={
                "request_id": str(request_id),
                "new_status": new_status,
            },
        )
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "ClientNotification status update failed · request_id=%s",
            request_id,
        )


# ════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════


router_admin = APIRouter(
    prefix="/admin/projects",
    tags=["Admin · Evidence Requests (Motor 7 · CLUSTER 3 Phase 3A)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.post(
    "/{project_id}/evidence-requests",
    response_model=EvidenceRequestResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def admin_create_request(
    project_id: uuid.UUID,
    body: EvidenceRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """Admin creates evidence request · status=pending_cliente · notify cliente."""
    await _set_admin_rls(db, str(project_id))
    client_id = await _resolve_client_id_from_project(db, str(project_id))

    row = await create_request(
        db,
        project_id=project_id,
        created_by_user_id=user.id,
        titulo=body.titulo,
        descripcion=body.descripcion,
        measure_code=body.measure_code,
        control_id=body.control_id,
        tipo_documento=body.tipo_documento,
        plantilla_url=body.plantilla_url,
        deadline_date=body.deadline_date,
        client_user_id=body.client_user_id,
    )

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=client_id,
        accion="admin.evidence_req.created",
        registro_id=str(row.id),
        usuario=str(user.id),
        payload={
            "titulo": row.titulo,
            "measure_code": row.measure_code,
            "deadline_date": row.deadline_date.isoformat() if row.deadline_date else None,
        },
    )

    await _notify_cliente_request_created(
        db,
        project_id=project_id,
        request_titulo=row.titulo,
        request_id=row.id,
        measure_code=row.measure_code,
    )

    await db.commit()
    return _to_response(row)


@router_admin.get(
    "/{project_id}/evidence-requests", response_model=EvidenceRequestList,
)
async def admin_list_requests(
    project_id: uuid.UUID,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Admin lists requests · filterable por status."""
    await _set_admin_rls(db, str(project_id))
    rows = await list_requests(
        db, project_id=project_id, status_filter=status_filter,
    )
    return EvidenceRequestList(requests=[_to_response(r) for r in rows])


@router_admin.get(
    "/{project_id}/evidence-requests/{request_id}",
    response_model=EvidenceRequestResponse,
)
async def admin_get_request(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Admin get request detail by id."""
    await _set_admin_rls(db, str(project_id))
    row = await get_request(db, request_id=request_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Evidence request not found")
    return _to_response(row)


@router_admin.post(
    "/{project_id}/evidence-requests/{request_id}/approve",
    response_model=EvidenceRequestResponse,
)
async def admin_approve_request(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """Admin approve uploaded evidence · state pending_review → approved."""
    await _set_admin_rls(db, str(project_id))
    client_id = await _resolve_client_id_from_project(db, str(project_id))

    try:
        row = await admin_approve(
            db, request_id=request_id, admin_user_id=user.id,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=client_id,
        accion="admin.evidence_req.approved",
        registro_id=str(row.id),
        usuario=str(user.id),
        payload={"titulo": row.titulo},
    )

    await _notify_cliente_status_update(
        db,
        project_id=project_id,
        client_user_id=row.client_user_id,
        request_titulo=row.titulo,
        request_id=row.id,
        new_status="approved",
    )

    await db.commit()
    return _to_response(row)


@router_admin.post(
    "/{project_id}/evidence-requests/{request_id}/reject",
    response_model=EvidenceRequestResponse,
)
async def admin_reject_request(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    body: RejectBody,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """Admin reject uploaded evidence · state pending_review → rejected · motivo claro."""
    await _set_admin_rls(db, str(project_id))
    client_id = await _resolve_client_id_from_project(db, str(project_id))

    try:
        row = await admin_reject(
            db, request_id=request_id, admin_user_id=user.id, motivo=body.motivo,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=client_id,
        accion="admin.evidence_req.rejected",
        registro_id=str(row.id),
        usuario=str(user.id),
        payload={"titulo": row.titulo, "motivo_preview": body.motivo[:200]},
    )

    await _notify_cliente_status_update(
        db,
        project_id=project_id,
        client_user_id=row.client_user_id,
        request_titulo=row.titulo,
        request_id=row.id,
        new_status="rejected",
        motivo=body.motivo,
    )

    await db.commit()
    return _to_response(row)


@router_admin.post(
    "/{project_id}/evidence-requests/{request_id}/cancel",
    response_model=EvidenceRequestResponse,
)
async def admin_cancel_request(
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """Admin cancel pending request · state pending_cliente → cancelled."""
    await _set_admin_rls(db, str(project_id))
    client_id = await _resolve_client_id_from_project(db, str(project_id))

    try:
        row = await admin_cancel(
            db, request_id=request_id, admin_user_id=user.id,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=client_id,
        accion="admin.evidence_req.cancelled",
        registro_id=str(row.id),
        usuario=str(user.id),
        payload={"titulo": row.titulo},
    )

    await db.commit()
    return _to_response(row)


# ════════════════════════════════════════════════════════════════════
# Cliente router (require_client_user · ADR-013 doble pool)
# ════════════════════════════════════════════════════════════════════


router_cliente = APIRouter(
    prefix="/client-portal/evidence-requests",
    tags=["Portal Cliente · Evidence Requests (CLUSTER 3 Phase 3A)"],
)


@router_cliente.get("", response_model=EvidenceRequestList)
async def cliente_list_requests(
    status_filter: Optional[str] = None,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente lists own pending evidence tasks · R29 friendly."""
    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await _set_cliente_rls(db, project_id=project_id_str, client_id=client_id_str)

    rows = await list_requests(
        db,
        project_id=uuid.UUID(project_id_str),
        status_filter=status_filter,
    )
    return EvidenceRequestList(requests=[_to_response(r) for r in rows])


@router_cliente.get(
    "/{request_id}", response_model=EvidenceRequestResponse,
)
async def cliente_get_request(
    request_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente view single task detail (R29 · NO admin lingo)."""
    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await _set_cliente_rls(db, project_id=project_id_str, client_id=client_id_str)

    row = await get_request(db, request_id=request_id)
    if row is None or str(row.project_id) != project_id_str:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    await _emit_audit_log(
        db,
        project_id=project_id_str,
        client_id=client_id_str,
        accion="cliente.evidence_req.viewed",
        registro_id=str(row.id),
        usuario=str(user.id),
    )
    await db.commit()
    return _to_response(row)


@router_cliente.post(
    "/{request_id}/upload", response_model=EvidenceRequestResponse,
)
async def cliente_upload_request(
    request_id: uuid.UUID,
    body: UploadLinkBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente link uploaded Evidence row to request · state → pending_review.

    Filosofía: cliente sube file via existing /client-portal/evidencias/upload
    (returns evidence_id) · then llama este endpoint para vincular al request
    (separa concerns: upload mechanics vs workflow linkage).
    """
    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await _set_cliente_rls(db, project_id=project_id_str, client_id=client_id_str)

    row = await get_request(db, request_id=request_id)
    if row is None or str(row.project_id) != project_id_str:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    try:
        row = await cliente_upload(
            db,
            request_id=request_id,
            evidence_id=body.evidence_id,
            client_user_id=user.id,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await _emit_audit_log(
        db,
        project_id=project_id_str,
        client_id=client_id_str,
        accion="cliente.evidence_req.uploaded",
        registro_id=str(row.id),
        usuario=str(user.id),
        payload={
            "evidence_id": str(body.evidence_id),
            "titulo": row.titulo,
        },
    )
    await db.commit()
    return _to_response(row)


@router_cliente.post(
    "/{request_id}/mark-na", response_model=EvidenceRequestResponse,
)
async def cliente_mark_na_request(
    request_id: uuid.UUID,
    body: MarkNaBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente marks request no aplicable + motivo amigable."""
    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await _set_cliente_rls(db, project_id=project_id_str, client_id=client_id_str)

    row = await get_request(db, request_id=request_id)
    if row is None or str(row.project_id) != project_id_str:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    try:
        row = await cliente_mark_na(
            db, request_id=request_id, client_user_id=user.id, motivo=body.motivo,
        )
    except WorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await _emit_audit_log(
        db,
        project_id=project_id_str,
        client_id=client_id_str,
        accion="cliente.evidence_req.markna",
        registro_id=str(row.id),
        usuario=str(user.id),
        payload={"motivo_preview": body.motivo[:200]},
    )
    await db.commit()
    return _to_response(row)
