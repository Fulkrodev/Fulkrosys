"""Cloud Remediation Orchestrator API · Bloque 3+5 v3.12.

Endpoints REST para orquestar approval workflow cloud remediation.

Admin endpoints (require_owner · project-scoped):
  POST   /admin/projects/{pid}/cloud-gaps/{gid}/propose-to-cliente
  POST   /admin/projects/{pid}/cloud-gaps/{gid}/execute
  POST   /admin/projects/{pid}/cloud-gaps/{gid}/mark-executed
  POST   /admin/projects/{pid}/cloud-gaps/{gid}/mark-failed
  GET    /admin/projects/{pid}/cloud-gaps/{gid}/audit-log

Cliente endpoints (require_client_user · ADR-013 doble pool):
  POST   /client-portal/cloud-gaps/{gid}/approve
  POST   /client-portal/cloud-gaps/{gid}/reject
  GET    /client-portal/cloud-gaps                            list pending approval

R23 sostener · admin endpoints project-scoped (`{pid}` URL param).
R29 firmísimo cliente · friendly response · NO presión coercitiva en errores.
ADR-013 doble pool auth respect.
ADR-031 ENAC trazabilidad audit log accesible via dedicated endpoint.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m_cloud_connectors.models import (
    CloudGap,
    CloudRemediationApprovalLog,
    CloudRemediationApprovalStatus,
)
from backend.app.motors.m_cloud_connectors.remediation_orchestrator import (
    CloudRemediationOrchestrator,
    GapNotFoundError,
    InvalidTransitionError,
)


# ──────────────────────────────────────────────────────────────────────
# Admin router · project-scoped


admin_router = APIRouter(
    prefix="/admin/projects/{project_id}/cloud-gaps",
    tags=["Cloud Remediation (Bloque 3+5) · Admin"],
    dependencies=[Depends(require_owner)],
)


# Cliente router · ADR-013 doble pool · NO project_id en URL (resolve via auth)


client_router = APIRouter(
    prefix="/client-portal/cloud-gaps",
    tags=["Cloud Remediation (Bloque 3+5) · Cliente"],
    dependencies=[Depends(require_client_user)],
)


# ──────────────────────────────────────────────────────────────────────
# Request bodies


class ProposeToClienteBody(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class StartExecutionBody(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class MarkExecutedBody(BaseModel):
    evidence_link_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class MarkFailedBody(BaseModel):
    error_notes: str = Field(..., min_length=3, max_length=4000)
    error_metadata: dict | None = None
    # Phase A Enhancement · failure_category obligatorio explícito
    failure_category: str | None = Field(
        default=None,
        description="One of: transient | permanent | partial | unknown",
    )
    correlation_id: uuid.UUID | None = None


class ClienteApproveBody(BaseModel):
    notes: str | None = Field(default=None, max_length=1500)


class ClienteRejectBody(BaseModel):
    notes: str | None = Field(default=None, max_length=1500)


# Phase A Enhancement · new request bodies


class MarkVerifiedBody(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    correlation_id: uuid.UUID | None = None


class RequestRollbackBody(BaseModel):
    reason: str = Field(..., min_length=3, max_length=2000)
    correlation_id: uuid.UUID | None = None


# ──────────────────────────────────────────────────────────────────────
# Helpers


async def _set_project_context(
    db: AsyncSession, project_id: uuid.UUID,
) -> None:
    """Set app.current_project_id + verify project exists (404 if not)."""
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, project_id=project_id)


async def _set_cliente_context_for_gap(
    db: AsyncSession, gap_id: uuid.UUID, cliente_user,
) -> CloudGap:
    """Resolve gap + verify cliente_user pertenece al project owner del gap.

    Returns gap si verification OK · raises 403/404 otherwise.
    """
    # Cliente NO sabe project_id y SOLO tiene el gap_id. cloud_gaps Y projects
    # están aislados por RLS bajo fulkro_app (FORCE), así que sin project_id no se
    # puede leer ninguno. Resolvemos la ownership con un bypass EXPLÍCITO y acotado
    # (igual que magic_link/list), verificamos pertenencia, y SOLO entonces fijamos
    # el contexto de tenant del cliente para operar bajo RLS normal.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        row = await db.execute(
            text(
                "SELECT cg.project_id, p.client_id "
                "FROM cloud_gaps cg JOIN projects p ON p.id = cg.project_id "
                "WHERE cg.id = :gid"
            ),
            {"gid": str(gap_id)},
        )
        hit = row.first()
    finally:
        await db.execute(text("RESET ROLE"))
    if hit is None:
        raise HTTPException(status_code=404, detail="Gap not found")

    gap_project_id, gap_client_id = hit
    cliente_client_id = getattr(cliente_user, "client_id", None)
    if cliente_client_id is None or str(cliente_client_id) != str(gap_client_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    await set_tenant_context(
        db, client_id=gap_client_id, project_id=gap_project_id,
    )

    # Reload bajo RLS context
    gap = await db.get(CloudGap, gap_id)
    if gap is None:
        raise HTTPException(status_code=404, detail="Gap not found")
    return gap


def _gap_to_dict(gap: CloudGap) -> dict[str, Any]:
    return {
        "id": str(gap.id),
        "project_id": str(gap.project_id),
        "ens_measure_code": gap.ens_measure_code,
        "severity": gap.severity,
        "title": gap.title,
        "explanation_es": gap.explanation_es,
        "suggested_action": gap.suggested_action,
        "approval_status": gap.approval_status,
        "proposed_to_cliente_at": (
            gap.proposed_to_cliente_at.isoformat()
            if gap.proposed_to_cliente_at else None
        ),
        "cliente_approval_at": (
            gap.cliente_approval_at.isoformat()
            if gap.cliente_approval_at else None
        ),
        "resolved_at": gap.resolved_at.isoformat() if gap.resolved_at else None,
        "evidence_link_id": (
            str(gap.evidence_link_id) if gap.evidence_link_id else None
        ),
        # Phase A Enhancement · verification lifecycle fields
        "verification_pending_at": (
            gap.verification_pending_at.isoformat()
            if gap.verification_pending_at else None
        ),
        "verified_at": gap.verified_at.isoformat() if gap.verified_at else None,
        "verified_by_user_id": (
            str(gap.verified_by_user_id) if gap.verified_by_user_id else None
        ),
    }


def _log_to_dict(log: CloudRemediationApprovalLog) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "gap_id": str(log.gap_id),
        "action": log.action,
        "actor_user_id": (
            str(log.actor_user_id) if log.actor_user_id else None
        ),
        "actor_type": log.actor_type,
        "notes": log.notes,
        "metadata": log.metadata_jsonb,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        # Phase A Enhancement · enriched audit fields
        "idempotency_key": log.idempotency_key,
        "failure_category": log.failure_category,
        "correlation_id": (
            str(log.correlation_id) if log.correlation_id else None
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# Admin endpoints


@admin_router.post("/{gap_id}/propose-to-cliente", status_code=200)
async def admin_propose_to_cliente(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: ProposeToClienteBody | None = None,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    orch = CloudRemediationOrchestrator(db)
    notes = body.notes if body else None
    try:
        gap = await orch.propose_to_cliente(
            gap_id=gap_id,
            admin_user_id=getattr(user, "id", None),
            notes=notes,
        )
    except GapNotFoundError:
        raise HTTPException(status_code=404, detail="Gap not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _gap_to_dict(gap)


@admin_router.post("/{gap_id}/execute", status_code=200)
async def admin_start_execution(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: StartExecutionBody | None = None,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    orch = CloudRemediationOrchestrator(db)
    notes = body.notes if body else None
    try:
        gap = await orch.start_execution(
            gap_id=gap_id,
            admin_user_id=getattr(user, "id", None),
            notes=notes,
        )
    except GapNotFoundError:
        raise HTTPException(status_code=404, detail="Gap not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _gap_to_dict(gap)


@admin_router.post("/{gap_id}/mark-executed", status_code=200)
async def admin_mark_executed(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: MarkExecutedBody | None = None,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin marks executed · auto-enters VERIFICATION_PENDING state (Phase A)."""
    await _set_project_context(db, project_id)
    orch = CloudRemediationOrchestrator(db)
    body = body or MarkExecutedBody()
    try:
        gap = await orch.mark_executed(
            gap_id=gap_id,
            admin_user_id=getattr(user, "id", None),
            evidence_link_id=body.evidence_link_id,
            notes=body.notes,
            auto_enter_verification=True,  # Phase A · production infallibility default
        )
    except GapNotFoundError:
        raise HTTPException(status_code=404, detail="Gap not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _gap_to_dict(gap)


@admin_router.post("/{gap_id}/mark-verified", status_code=200)
async def admin_mark_verified(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: MarkVerifiedBody | None = None,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Phase A Enhancement · admin reports verify success post-execute.

    Transition: verification_pending → verified [TERMINAL].
    Dispatches system_consciousness hook (Phase B cross-system propagation).
    """
    await _set_project_context(db, project_id)
    orch = CloudRemediationOrchestrator(db)
    body = body or MarkVerifiedBody()
    try:
        gap = await orch.mark_verified(
            gap_id=gap_id,
            admin_user_id=getattr(user, "id", None),
            notes=body.notes,
            correlation_id=body.correlation_id,
        )
    except GapNotFoundError:
        raise HTTPException(status_code=404, detail="Gap not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _gap_to_dict(gap)


@admin_router.post("/{gap_id}/request-rollback", status_code=200)
async def admin_request_rollback(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: RequestRollbackBody,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Phase A Enhancement · admin reports verify failed · transitions back to EXECUTING.

    Admin manually rollback cloud action externa + re-execute · ADR-014 sostained.
    """
    await _set_project_context(db, project_id)
    orch = CloudRemediationOrchestrator(db)
    try:
        gap = await orch.request_rollback(
            gap_id=gap_id,
            admin_user_id=getattr(user, "id", None),
            reason=body.reason,
            correlation_id=body.correlation_id,
        )
    except GapNotFoundError:
        raise HTTPException(status_code=404, detail="Gap not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _gap_to_dict(gap)


@admin_router.post("/{gap_id}/mark-failed", status_code=200)
async def admin_mark_failed(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: MarkFailedBody,
    user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin marks failed · Phase A Enhancement con failure_category + correlation_id."""
    await _set_project_context(db, project_id)
    orch = CloudRemediationOrchestrator(db)
    try:
        gap = await orch.mark_failed(
            gap_id=gap_id,
            admin_user_id=getattr(user, "id", None),
            error_notes=body.error_notes,
            error_metadata=body.error_metadata,
            failure_category=body.failure_category,
            correlation_id=body.correlation_id,
        )
    except GapNotFoundError:
        raise HTTPException(status_code=404, detail="Gap not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return _gap_to_dict(gap)


@admin_router.get("/{gap_id}/audit-log", status_code=200)
async def admin_list_audit_log(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_context(db, project_id)
    # Verify gap exists en este project
    gap = await db.get(CloudGap, gap_id)
    if gap is None or gap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Gap not found")
    orch = CloudRemediationOrchestrator(db)
    logs = await orch.list_audit_logs(gap_id=gap_id)
    return {
        "gap_id": str(gap_id),
        "project_id": str(project_id),
        "count": len(logs),
        "logs": [_log_to_dict(l) for l in logs],
    }


# ──────────────────────────────────────────────────────────────────────
# Cliente endpoints


@client_router.post("/{gap_id}/approve", status_code=200)
async def cliente_approve_remediation(
    gap_id: uuid.UUID,
    body: ClienteApproveBody | None = None,
    cliente_user=Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cliente aprueba propuesta · friendly response R29 sostained."""
    gap = await _set_cliente_context_for_gap(db, gap_id, cliente_user)
    orch = CloudRemediationOrchestrator(db)
    notes = body.notes if body else None
    try:
        gap = await orch.cliente_approve(
            gap_id=gap_id,
            cliente_user_id=getattr(cliente_user, "id", None),
            notes=notes,
        )
    except InvalidTransitionError:
        # R29 friendly · NO jerga técnica al cliente
        raise HTTPException(
            status_code=409,
            detail="Esta propuesta ya no está pendiente de tu aprobación.",
        )
    await db.commit()
    return {
        "gap_id": str(gap.id),
        "approval_status": gap.approval_status,
        "friendly_message": "¡Gracias! Marcos comenzará a ejecutar pronto.",
    }


@client_router.post("/{gap_id}/reject", status_code=200)
async def cliente_reject_remediation(
    gap_id: uuid.UUID,
    body: ClienteRejectBody | None = None,
    cliente_user=Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    gap = await _set_cliente_context_for_gap(db, gap_id, cliente_user)
    orch = CloudRemediationOrchestrator(db)
    notes = body.notes if body else None
    try:
        gap = await orch.cliente_reject(
            gap_id=gap_id,
            cliente_user_id=getattr(cliente_user, "id", None),
            notes=notes,
        )
    except InvalidTransitionError:
        raise HTTPException(
            status_code=409,
            detail="Esta propuesta ya no está pendiente de tu decisión.",
        )
    await db.commit()
    return {
        "gap_id": str(gap.id),
        "approval_status": gap.approval_status,
        "friendly_message": "Entendido · Marcos lo tendrá en cuenta.",
    }


@client_router.get("", status_code=200)
async def cliente_list_pending_remediations(
    cliente_user=Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List gaps pendientes de aprobación cliente · feed UI portal."""
    cliente_client_id = getattr(cliente_user, "client_id", None)
    if cliente_client_id is None:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Resolve project_id del cliente · single-project assumption per 1.E.2.bis.
    # projects tiene FORCE RLS por current_client_id(): fijar app.current_client_id
    # ANTES de leerla (si no, 0 filas → el cliente vería SIEMPRE 0 remediaciones).
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(cliente_client_id)},
    )
    row = await db.execute(
        text(
            "SELECT id FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at ASC LIMIT 1"
        ),
        {"cid": str(cliente_client_id)},
    )
    project_row = row.first()
    if project_row is None:
        return {"project_id": None, "count": 0, "gaps": []}

    project_id = project_row[0]
    await set_tenant_context(db, project_id=project_id)

    result = await db.execute(
        select(CloudGap)
        .where(CloudGap.project_id == project_id)
        .where(CloudGap.cliente_can_see.is_(True))
        .where(
            CloudGap.approval_status.in_([
                CloudRemediationApprovalStatus.PROPOSED_TO_CLIENTE.value,
                CloudRemediationApprovalStatus.APPROVED.value,
                CloudRemediationApprovalStatus.EXECUTING.value,
                CloudRemediationApprovalStatus.EXECUTED.value,
            ])
        )
        .where(CloudGap.deleted_at.is_(None))
        .order_by(CloudGap.proposed_to_cliente_at.desc().nullslast())
    )
    gaps = list(result.scalars().all())

    return {
        "project_id": str(project_id),
        "count": len(gaps),
        "gaps": [_gap_to_dict(g) for g in gaps],
    }
