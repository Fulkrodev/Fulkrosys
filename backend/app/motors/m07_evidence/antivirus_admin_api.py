"""M07 antivirus admin endpoints · SAN-E v3.MB-6 atom 6 FASE 3.

Admin quarantine review workflow (Q2 B false-positive recoverable):
- GET    /admin/evidence/quarantined                       · list quarantined
- POST   /admin/evidence/{id}/release-quarantined          · restore false-positive
- DELETE /admin/evidence/{id}/permanent-delete-quarantined · cleanup definitivo

Auth: require_owner (admin Marcos · pattern atomic m05/m06 etc.).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.motors.m07_evidence.antivirus_scan_service import (
    EvidenceNotFoundError,
    InvalidQuarantineActionError,
    admin_permanent_delete_quarantined,
    admin_release_quarantined,
    list_quarantined,
)


router = APIRouter(
    prefix="/admin/evidence",
    tags=["Motor 07 - Evidence antivirus admin"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class QuarantinedItemOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    fichero_nombre_original: str | None
    scan_completed_at: datetime | None
    virus_name: str | None
    duration_ms: int | None


class QuarantineActionOut(BaseModel):
    evidence_id: uuid.UUID
    new_scan_status: str
    admin_user_id: uuid.UUID


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _to_item(row: dict) -> QuarantinedItemOut:
    scan_result = row.get("scan_result_jsonb") or {}
    return QuarantinedItemOut(
        id=row["id"],
        project_id=row["project_id"],
        fichero_nombre_original=row.get("fichero_nombre_original"),
        scan_completed_at=row.get("scan_completed_at"),
        virus_name=scan_result.get("virus_name") if isinstance(scan_result, dict) else None,
        duration_ms=scan_result.get("duration_ms") if isinstance(scan_result, dict) else None,
    )


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EvidenceNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, InvalidQuarantineActionError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/quarantined",
    response_model=list[QuarantinedItemOut],
)
async def list_quarantined_evidence(
    project_id: uuid.UUID | None = Query(
        None,
        description="Optional filter por proyecto · None=todos los proyectos",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[QuarantinedItemOut]:
    """Lista archivos en cuarentena · admin Marcos review queue."""
    rows = await list_quarantined(db, project_id=project_id)
    return [_to_item(r) for r in rows]


@router.post(
    "/{evidence_id}/release-quarantined",
    response_model=QuarantineActionOut,
)
async def release_quarantined(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> QuarantineActionOut:
    """Marcos restaura false-positive · file vuelve a evidencias activas."""
    try:
        await admin_release_quarantined(db, evidence_id, user.id)
    except (EvidenceNotFoundError, InvalidQuarantineActionError) as exc:
        raise _handle_service_error(exc) from exc
    await db.commit()
    return QuarantineActionOut(
        evidence_id=evidence_id,
        new_scan_status="clean",
        admin_user_id=user.id,
    )


@router.delete(
    "/{evidence_id}/permanent-delete-quarantined",
    status_code=status.HTTP_200_OK,
    response_model=QuarantineActionOut,
)
async def permanent_delete_quarantined(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> QuarantineActionOut:
    """Marcos confirma amenaza · delete file disk + soft-delete evidence row."""
    try:
        await admin_permanent_delete_quarantined(db, evidence_id, user.id)
    except (EvidenceNotFoundError, InvalidQuarantineActionError) as exc:
        raise _handle_service_error(exc) from exc
    await db.commit()
    return QuarantineActionOut(
        evidence_id=evidence_id,
        new_scan_status="deleted",
        admin_user_id=user.id,
    )
