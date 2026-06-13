"""AuditLog admin endpoints (ADR-038 SAN-D MB-14.1).

3 endpoints admin:
- GET /projects/{id}/client-audit            · lista acciones cliente
- GET /projects/{id}/client-audit/integrity  · verifica hash chain
- GET /projects/{id}/client-audit/export     · export JSON auditor externo
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m21_portal_cliente.audit_log_service import (
    AuditLogService,
)

router = APIRouter(tags=["MB-14 - Client Audit Log (hash chain)"])


# FIX(RLS): client_user_audit es RLS por client_id. Sin tenant context el
# SELECT no ve filas (lista vacía AND verify_chain_integrity reporta
# chain_valid=True sobre 0 filas · falso positivo de seguridad). Resolvemos
# el owner via get_project_owner (SECURITY DEFINER) y fijamos el contexto
# RLS antes de cualquier query.
async def _ensure_project_scope(db: AsyncSession, project_id: UUID) -> None:
    owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"),
            {"pid": str(project_id)},
        )
    ).scalar()
    if not owner:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=owner, project_id=project_id)


@router.get("/projects/{project_id}/client-audit")
async def list_client_audit(
    project_id: UUID,
    client_user_id: Optional[UUID] = None,
    action_type: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> list[dict]:
    """Admin lista audit log cliente filtrado."""
    await _ensure_project_scope(db, project_id)
    service = AuditLogService(db)
    actions = await service.list_actions(
        project_id=project_id,
        client_user_id=client_user_id,
        action_type=action_type,
        limit=limit,
    )
    return [
        {
            "id": str(a.id),
            "client_user_id": str(a.client_user_id) if a.client_user_id else None,
            "action_type": a.action_type or a.action,
            "action_data": a.metadata_jsonb,
            "ip_address": str(a.ip_address) if a.ip_address else None,
            "chain_index": a.chain_index,
            "current_hash": a.current_hash,
            "user_agent": a.user_agent,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


@router.get("/projects/{project_id}/client-audit/integrity")
async def verify_audit_integrity(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    """Verifica integridad hash chain audit log (rows con chain_index)."""
    await _ensure_project_scope(db, project_id)
    service = AuditLogService(db)
    is_valid, broken_at = await service.verify_chain_integrity(project_id)
    return {
        "project_id": str(project_id),
        "chain_valid": is_valid,
        "broken_at_index": broken_at,
    }


@router.get("/projects/{project_id}/client-audit/export")
async def export_audit_chain(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    """Export JSON completo chain (audit externo)."""
    await _ensure_project_scope(db, project_id)
    service = AuditLogService(db)
    return await service.export_chain(project_id)
