"""M25 Paso 4 API endpoints — lifecycle cierre honesto + backups descargables.

Endpoints:

Cockpit Marcos (admin-scope):
  POST /api/v1/projects/{id}/mark-certified
  POST /api/v1/projects/{id}/lifecycle/offer-retainer
  POST /api/v1/projects/{id}/lifecycle/start-grace-period
  GET  /api/v1/projects/{id}/lifecycle/status
  GET  /api/v1/projects/{id}/lifecycle/events
  POST /api/v1/projects/{id}/lifecycle/generate-backup

Cliente via magic link:
  POST /api/v1/projects/{id}/lifecycle/decision
  GET  /api/v1/archived-backups/{id}/download
  POST /api/v1/archived-backups/{id}/reactivate
"""
from __future__ import annotations

import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .lifecycle_paso4 import (
    BACKUP_DOWNLOAD_TTL_DAYS,
    GRACE_PERIOD_DAYS_DEFAULT,
    LifecyclePaso4Error,
    LifecyclePaso4Service,
    VALID_DECISIONS,
    VALID_RETAINER_TIERS,
    get_archived_backup,
)


router = APIRouter(
    tags=["Motor 25 - Lifecycle Paso 4"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Establece tenant context para el proyecto. Usa get_project_owner().

    ``get_project_owner`` es una SECURITY DEFINER function que bypasa RLS
    para devolver el client_id del proyecto. Se usa en el resto de
    motores M25 / M10 / etc.
    """
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    cid = (
        client_id if isinstance(client_id, uuid.UUID)
        else uuid.UUID(str(client_id))
    )
    await set_tenant_context(db, client_id=cid, project_id=project_id)
    return cid


# ══════════════════════════════════════════════════════════════════════
# Schemas
# ══════════════════════════════════════════════════════════════════════


class MarkCertifiedBody(BaseModel):
    certified_on: str | None = Field(
        default=None,
        description="Fecha ISO (YYYY-MM-DD). Si es None, usa today.",
    )


class OfferRetainerBody(BaseModel):
    recipient_email: EmailStr
    base_url: str = "https://portal.fulkro.es"


class RetainerDecisionBody(BaseModel):
    decision: str = Field(..., description=f"Valores: {VALID_DECISIONS}")
    tier: str | None = Field(None, description=f"Requerido si accept: {VALID_RETAINER_TIERS}")
    precio_mensual: float = Field(0.0, ge=0)
    performed_by: str = "cliente"


class StartGraceBody(BaseModel):
    days: int = Field(GRACE_PERIOD_DAYS_DEFAULT, ge=1, le=365 * 2)
    decision: str | None = "decline"


class GenerateBackupBody(BaseModel):
    recipient_email: EmailStr | None = None
    base_url: str = "https://portal.fulkro.es"
    send_magic_link: bool = True


class ReactivateBody(BaseModel):
    new_project_name: str | None = None


class MarkAuditPassedBody(BaseModel):
    """Sesión 3B-2B.6 Cluster 1 Phase 2 · admin mark audit result.

    Marcos marca resultado auditoría ENAC post entrega ZIP firmado + feedback
    auditor offline. Si result=='passed' AND NOT yet certified · cadena
    mark_certified() automatic (lifecycle CERTIFIED transition).
    """
    result: str = Field(
        ...,
        description="passed | observed | correction_required | failed",
    )
    audit_report_ref: str | None = Field(
        None,
        max_length=120,
        description="Reference auditor (e.g. 'E-702-AUD-001' · ENAC cert number)",
    )
    cascade_certify: bool = Field(
        True,
        description="Si True AND result=='passed' AND NOT certified · auto mark_certified",
    )
    cascade_retainer_offer: bool = Field(
        True,
        description=(
            "Si True AND cascade_certify exitoso · auto offer_retainer "
            "(Sesión 3B-2B.6 Cluster 1 Phase 3 trigger automation)"
        ),
    )
    performed_by: str = Field(
        "marcos", max_length=255,
        description="Admin que marca · default Marcos owner",
    )


# ══════════════════════════════════════════════════════════════════════
# Cockpit Marcos
# ══════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/mark-certified",
    status_code=status.HTTP_201_CREATED,
)
async def mark_certified(
    project_id: uuid.UUID,
    body: MarkCertifiedBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    certified_on = None
    if body.certified_on:
        from datetime import date as date_cls
        try:
            certified_on = date_cls.fromisoformat(body.certified_on)
        except ValueError as exc:
            raise HTTPException(400, f"certified_on invalido: {exc}")
    try:
        event = await LifecyclePaso4Service().mark_certified(
            db, project_id, certified_on=certified_on,
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "certified_at": (event.metadata_jsonb or {}).get("certified_on"),
    }


@router.post(
    "/projects/{project_id}/audit/mark-passed",
    status_code=status.HTTP_201_CREATED,
)
async def mark_audit_passed(
    project_id: uuid.UUID,
    body: MarkAuditPassedBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin marca resultado auditoría ENAC + state transition opcional.

    Sesión 3B-2B.6 Cluster 1 Phase 2 · audit Phase 0 DIM 4 critical gap A resolved.

    Flujo:
    1. Marcos entrega ZIP firmado (Phase 1) al auditor ENAC
    2. Auditor revisa offline · feedback resultado
    3. Marcos POST /audit/mark-passed con result + audit_report_ref
    4. Backend records audit_passed_at + audit_passed_by + audit_result + report_ref
    5. Si result='passed' AND NOT certified · auto mark_certified (cascade)
    6. Lifecycle event 'audit_marked' + opcional 'certified' emitted
    7. Phase 3 workflow hook listens audit_marked + result=passed → retainer offer

    Idempotency: si audit ya marked · returns 400 con timestamp existente.
    """
    await _set_project_rls(project_id, db)
    try:
        result = await LifecyclePaso4Service().mark_audit_passed(
            db, project_id,
            result=body.result,
            audit_report_ref=body.audit_report_ref,
            performed_by=body.performed_by,
            cascade_certify=body.cascade_certify,
            cascade_retainer_offer=body.cascade_retainer_offer,
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return result


@router.post("/projects/{project_id}/lifecycle/offer-retainer")
async def offer_retainer(
    project_id: uuid.UUID,
    body: OfferRetainerBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        result = await LifecyclePaso4Service().offer_retainer(
            db, project_id,
            recipient_email=str(body.recipient_email),
            base_url=body.base_url,
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return result


@router.post("/projects/{project_id}/lifecycle/start-grace-period")
async def start_grace_period(
    project_id: uuid.UUID,
    body: StartGraceBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        event = await LifecyclePaso4Service().start_grace_period(
            db, project_id,
            days=body.days,
            decision=body.decision,
            performed_by="marcos",
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "event_id": str(event.id),
        "grace_period_days": event.grace_period_days,
        "event_type": event.event_type,
    }


@router.get("/projects/{project_id}/lifecycle/status")
async def lifecycle_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        return await LifecyclePaso4Service().get_lifecycle_status(db, project_id)
    except LifecyclePaso4Error as exc:
        raise HTTPException(404, str(exc))


@router.get("/projects/{project_id}/lifecycle/events")
async def lifecycle_events(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    events = await LifecyclePaso4Service().get_lifecycle_events(db, project_id)
    return {
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "performed_by": e.performed_by,
                "grace_period_days": e.grace_period_days,
                "metadata": e.metadata_jsonb,
                "notification_sent_to": e.notification_sent_to,
            }
            for e in events
        ],
    }


@router.post(
    "/projects/{project_id}/lifecycle/generate-backup",
    status_code=status.HTTP_201_CREATED,
)
async def generate_backup(
    project_id: uuid.UUID,
    body: GenerateBackupBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        backup = await LifecyclePaso4Service().generate_project_backup_zip(
            db, project_id,
            recipient_email=str(body.recipient_email) if body.recipient_email else None,
            base_url=body.base_url,
            performed_by="marcos",
            send_magic_link=body.send_magic_link and body.recipient_email is not None,
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return {
        "backup_id": str(backup.id),
        "zip_path": backup.zip_path,
        "sha256": backup.sha256_hash,
        "size_bytes": backup.zip_size_bytes,
        "expires_at": backup.expires_at.isoformat(),
        "download_ttl_days": BACKUP_DOWNLOAD_TTL_DAYS,
    }


# ══════════════════════════════════════════════════════════════════════
# Cliente (via magic link context)
# ══════════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/lifecycle/decision")
async def retainer_decision(
    project_id: uuid.UUID,
    body: RetainerDecisionBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        result = await LifecyclePaso4Service().handle_retainer_decision(
            db, project_id,
            decision=body.decision,
            tier=body.tier,
            precio_mensual=body.precio_mensual,
            performed_by=body.performed_by,
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return result


@router.get("/archived-backups/{archived_backup_id}/download")
async def download_archived_backup(
    archived_backup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Devuelve el ZIP del backup. Autorizacion TODO via magic link consume.

    El flujo real exige que el cliente ya haya consumido un magic link
    ``DESCARGA_BACKUP_ARCHIVO`` y este endpoint se llame con el token
    validado. Aqui por simplicidad se descarga directo por archived id
    (el RLS + la TTL del backup actuan como defense in depth).
    """
    backup = await get_archived_backup(db, archived_backup_id)
    if backup is None:
        raise HTTPException(404, "Archived backup no encontrado")
    if backup.deleted_at is not None:
        raise HTTPException(410, "Backup eliminado del almacenamiento")

    from datetime import datetime, timezone as tz
    if backup.expires_at and backup.expires_at < datetime.now(tz.utc):
        raise HTTPException(410, "Backup expirado")

    zip_path = backup.zip_path
    zip_bytes: bytes
    if zip_path.startswith("minio://"):
        from backend.app.core.storage.minio_client import get_object
        rest = zip_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        try:
            zip_bytes = get_object(bucket, key)
        except Exception as exc:
            raise HTTPException(
                502, f"MinIO unreachable: {exc}",
            )
    else:
        # dev / tests: re-generar desde manifest (no hay ZIP fisico)
        raise HTTPException(
            503,
            "ZIP no disponible en este entorno (local://). "
            "Verifique la configuracion de MinIO.",
        )

    # Incrementar counter + downloaded_at
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        await db.execute(
            sa_text(
                "UPDATE project_archived_backups "
                "SET downloaded_at = now(), "
                "download_count = COALESCE(download_count, 0) + 1 "
                "WHERE id = :bid"
            ),
            {"bid": str(backup.id)},
        )
        await db.flush()
    finally:
        await db.execute(sa_text("RESET ROLE"))

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename=backup_{backup.id}.zip"
            ),
            "X-Backup-SHA256": backup.sha256_hash,
            "X-Backup-Signature-Ed25519": backup.ed25519_signature,
        },
    )


@router.post(
    "/archived-backups/{archived_backup_id}/reactivate",
    status_code=status.HTTP_201_CREATED,
)
async def reactivate_from_backup(
    archived_backup_id: uuid.UUID,
    body: ReactivateBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        result = await LifecyclePaso4Service().reactivate_project(
            db,
            archived_backup_id=archived_backup_id,
            new_project_name=body.new_project_name,
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return result
