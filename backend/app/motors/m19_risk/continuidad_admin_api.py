"""Continuidad admin API · feat/fulkro-100 Ola A · remate buzón + notify.

Cierra el loop de sync de continuidad (BIA/DRP). El cliente rellena su
cuestionario (RTO/RPO, procesos críticos, activos) y comenta/aprueba los
borradores desde su portal; aquí Marcos (require_owner) VE ese buzón —qué
envió y qué aprobó/comentó— y, cuando deja un borrador BIA/DRP listo, NOTIFICA
al cliente con el evento SSE ``continuidad.draft_ready`` que refresca su portal
en realtime (Pattern #14 · admin-origin · cliente-facing).

Antes de este remate el lado admin solo podía crear entries BIA (bia_api) pero
NO veía el cuestionario del cliente ni cerraba el bucle hacia el cliente.

ADR-013 doble pool · require_owner. audit_log Sub-atom 5.A 3-way OR.
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db, set_tenant_context
from backend.app.models.auth import User
from backend.app.models.cliente_continuidad import ClienteContinuidadApproval
from backend.app.motors.m19_risk.cliente_continuidad_service import get_input

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/projects",
    tags=["M19 - Continuidad (admin buzón)"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class QuestionnaireBuzon(BaseModel):
    submitted_at: str
    updated_at: str
    procesos_criticos: Optional[list[dict]] = None
    rto_horas_tolerancia: Optional[int] = None
    rpo_horas_tolerancia: Optional[int] = None
    impacto_diario_eur: Optional[str] = None
    activos_core: Optional[list[dict]] = None
    notas_cliente: Optional[str] = None
    completed: bool


class ApprovalBuzon(BaseModel):
    id: str
    artifact_type: str
    draft_id: Optional[str] = None
    action: str
    comment_text: Optional[str] = None
    created_at: str


class BuzonResponse(BaseModel):
    has_questionnaire: bool
    questionnaire: Optional[QuestionnaireBuzon] = None
    approvals: list[ApprovalBuzon]
    pending_comments: int


class NotifyDraftReadyBody(BaseModel):
    artifact_type: str = Field("bia", pattern="^(bia|drp)$")
    draft_id: Optional[uuid.UUID] = None
    message: Optional[str] = Field(None, max_length=2000)


class NotifyDraftReadyResponse(BaseModel):
    ok: bool
    event_type: str


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _ensure_project_and_client(
    db: AsyncSession, project_id: uuid.UUID,
) -> str:
    """Verifica que el proyecto existe + devuelve su client_id (str).

    Setea además el contexto RLS (project + client) para que el admin pueda
    leer las filas escritas por el cliente aunque las tablas
    ``cliente_continuidad_*`` tengan RLS por tenant (defensivo · inocuo si el
    rol del runtime hace BYPASSRLS).
    """
    # FIX(RLS): resolve owner via get_project_owner (SECURITY DEFINER) BEFORE
    # any RLS query — db.get(Project) here ran under fulkro_app RLS without
    # app.current_project_id set yet → filtered out → spurious 404.
    client_id = (
        await db.execute(
            text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    client_id = str(client_id)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return client_id


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: str,
    accion: str,
    usuario: str,
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
                "usuario": usuario,
                "pid": project_id,
                "cid": client_id,
                "payload": _json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log %s emit failed · pid=%s", accion, project_id)


# ════════════════════════════════════════════════════════════════════
# Endpoints admin
# ════════════════════════════════════════════════════════════════════


@router.get("/{project_id}/continuidad/buzon", response_model=BuzonResponse)
async def get_buzon(
    project_id: uuid.UUID,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> BuzonResponse:
    """Marcos VE el buzón de continuidad del cliente: cuestionario + decisiones.

    Devuelve el cuestionario que envió el cliente (RTO/RPO, procesos, activos,
    notas) y la lista de aprobaciones/comentarios sobre los borradores BIA/DRP,
    más cuántos comentarios (peticiones de cambio) hay pendientes de atender.
    """
    await _ensure_project_and_client(db, project_id)

    row = await get_input(db, project_id=project_id)
    questionnaire: Optional[QuestionnaireBuzon] = None
    if row is not None:
        questionnaire = QuestionnaireBuzon(
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

    approval_rows = (await db.execute(
        select(ClienteContinuidadApproval)
        .where(ClienteContinuidadApproval.project_id == project_id)
        .order_by(ClienteContinuidadApproval.created_at.desc())
    )).scalars().all()
    approvals = [
        ApprovalBuzon(
            id=str(a.id),
            artifact_type=a.artifact_type,
            draft_id=str(a.draft_id) if a.draft_id is not None else None,
            action=a.action,
            comment_text=a.comment_text,
            created_at=a.created_at.isoformat(),
        )
        for a in approval_rows
    ]
    pending_comments = sum(1 for a in approval_rows if a.action == "comment")

    return BuzonResponse(
        has_questionnaire=questionnaire is not None,
        questionnaire=questionnaire,
        approvals=approvals,
        pending_comments=pending_comments,
    )


@router.post(
    "/{project_id}/continuidad/notify-draft-ready",
    response_model=NotifyDraftReadyResponse,
)
async def notify_draft_ready(
    project_id: uuid.UUID,
    body: NotifyDraftReadyBody,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> NotifyDraftReadyResponse:
    """Marcos deja un borrador BIA/DRP listo y avisa al cliente (realtime).

    Emite ``continuidad.draft_ready`` por el canal ``project:{id}`` → el portal
    del cliente (que ya escucha ese evento) refresca su lista de borradores y le
    invita a revisarlo/aprobarlo. NO modifica el borrador en sí (eso es BIA/DRP);
    solo cierra el bucle de notificación admin→cliente.
    """
    client_id = await _ensure_project_and_client(db, project_id)

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=client_id,
        accion="admin.continuidad.draft_ready",
        usuario=getattr(owner, "email", "admin") or "admin",
        registro_id=str(body.draft_id) if body.draft_id else None,
        payload={
            "artifact_type": body.artifact_type,
            "draft_id": str(body.draft_id) if body.draft_id else None,
        },
    )
    await db.commit()

    # SSE SIEMPRE después del commit (Pattern #14 · nunca evento fantasma).
    try:
        await sse_dispatcher.dispatch(
            f"project:{project_id}",
            "continuidad.draft_ready",
            {
                "primary_actor": "admin",
                "artifact_type": body.artifact_type,
                "draft_id": str(body.draft_id) if body.draft_id else None,
                "message": body.message,
            },
        )
    except Exception:  # pragma: no cover · best-effort
        logger.warning("SSE continuidad.draft_ready dispatch failed (best-effort)")

    return NotifyDraftReadyResponse(
        ok=True, event_type="continuidad.draft_ready",
    )
