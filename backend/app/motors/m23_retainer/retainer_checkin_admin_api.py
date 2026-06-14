"""Retainer check-in · ADMIN curación API (feat/fulkro-100 · Ola 3).

Cierra el P0 del retainer: ``generate_quarterly_report_draft`` /
``admin_curate_report`` / ``admin_send_to_client`` existían en el servicio pero
SIN endpoint admin → Marcos no podía listar, generar, curar ni ENVIAR los
check-ins trimestrales al cliente (solo los llamaban los tests + el beat Celery).

Workflow: draft → curated_by_admin → sent_to_client (→ cliente revisa).
ADR-013 require_owner (pool admin). R23 project-scoped.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.database import get_db, set_tenant_context
from backend.app.models.auth import User
from backend.app.models.retainer import RetainerQuarterlyReport
from backend.app.motors.m23_retainer.retainer_checkin_service import (
    CheckinReportNotFoundError,
    InvalidWorkflowTransitionError,
    NoActiveRetainerError,
    RetainerCheckinService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/retainer-checkin",
    tags=["Motor 23 - Retainer check-in (admin curación)"],
    dependencies=[Depends(require_owner)],
)


# ──────────────────────────────────────────────────────────────────────
# Schemas


class CheckinReportOut(BaseModel):
    id: str
    project_id: str
    period_quarter: str
    admin_curation_status: str
    summary_jsonb: dict
    admin_curated_at: Optional[str] = None
    sent_at: Optional[str] = None
    client_review_status: Optional[str] = None
    created_at: Optional[str] = None


class GenerateBody(BaseModel):
    period_quarter: Optional[str] = None


class CurateBody(BaseModel):
    summary_edits: Optional[dict] = None


def _to_out(r: RetainerQuarterlyReport) -> CheckinReportOut:
    return CheckinReportOut(
        id=str(r.id),
        project_id=str(r.project_id),
        period_quarter=r.period_quarter,
        admin_curation_status=r.admin_curation_status,
        summary_jsonb=dict(r.summary_jsonb or {}),
        admin_curated_at=(
            r.admin_curated_at.isoformat() if r.admin_curated_at else None
        ),
        sent_at=r.sent_at.isoformat() if r.sent_at else None,
        client_review_status=getattr(r, "client_review_status", None),
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


async def _set_rls_for_report(db: AsyncSession, report_id: uuid.UUID) -> None:
    """FIX(RLS): los endpoints report_id-scoped (get/curate/send) reciben
    report_id sin project_id en la ruta. Resolver el project_id del check-in
    (cruzando RLS vía bypass admin acotado) + fijar tenant context, si no
    retainer_quarterly_reports (RLS fail-closed bajo fulkro_app) → None → 404."""
    await db.execute(_sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        pid = (
            await db.execute(
                _sa_text(
                    "SELECT project_id FROM retainer_quarterly_reports "
                    "WHERE id = :rid"
                ),
                {"rid": str(report_id)},
            )
        ).scalar()
    finally:
        await db.execute(_sa_text("RESET ROLE"))
    if not pid:
        raise HTTPException(404, "Check-in no existe")
    owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(pid)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(404, "Check-in no existe")
    await set_tenant_context(db, client_id=owner, project_id=pid)


# ──────────────────────────────────────────────────────────────────────
# Endpoints (admin · require_owner a nivel de router)


@router.get(
    "/projects/{project_id}/reports", response_model=list[CheckinReportOut],
)
async def list_reports(
    project_id: uuid.UUID, db: AsyncSession = Depends(get_db),
) -> list[CheckinReportOut]:
    """Lista los check-ins trimestrales de un proyecto (cualquier estado)."""
    # FIX(RLS): resolver owner vía SECURITY DEFINER + set tenant context ANTES
    # de la query (retainer_quarterly_reports tiene RLS · fulkro_app enforced).
    _owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not _owner:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=_owner, project_id=project_id)
    rows = (
        await db.execute(
            select(RetainerQuarterlyReport)
            .where(RetainerQuarterlyReport.project_id == project_id)
            .order_by(RetainerQuarterlyReport.period_quarter.desc())
        )
    ).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/reports/{report_id}", response_model=CheckinReportOut)
async def get_report(
    report_id: uuid.UUID, db: AsyncSession = Depends(get_db),
) -> CheckinReportOut:
    await _set_rls_for_report(db, report_id)
    r = await db.get(RetainerQuarterlyReport, report_id)
    if r is None:
        raise HTTPException(404, "Check-in no existe")
    return _to_out(r)


@router.post(
    "/projects/{project_id}/reports/generate",
    response_model=CheckinReportOut, status_code=201,
)
async def generate_report(
    project_id: uuid.UUID,
    body: GenerateBody = Body(default_factory=GenerateBody),
    db: AsyncSession = Depends(get_db),
) -> CheckinReportOut:
    """Genera (idempotente) el borrador del check-in trimestral."""
    # FIX(RLS): resolver owner vía SECURITY DEFINER + set tenant context ANTES
    # del service (lee/escribe retainer_quarterly_reports con RLS · fulkro_app).
    _owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not _owner:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=_owner, project_id=project_id)
    try:
        r = await RetainerCheckinService(db).generate_quarterly_report_draft(
            project_id, body.period_quarter,
        )
    except NoActiveRetainerError as exc:
        raise HTTPException(400, str(exc)) from exc
    await db.commit()
    return _to_out(r)


@router.post("/reports/{report_id}/curate", response_model=CheckinReportOut)
async def curate_report(
    report_id: uuid.UUID,
    body: CurateBody = Body(default_factory=CurateBody),
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> CheckinReportOut:
    """Marcos cura el borrador (edita el resumen) · draft → curated_by_admin."""
    await _set_rls_for_report(db, report_id)
    try:
        r = await RetainerCheckinService(db).admin_curate_report(
            report_id, owner.id, body.summary_edits,
        )
    except CheckinReportNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidWorkflowTransitionError as exc:
        raise HTTPException(409, str(exc)) from exc
    await db.commit()

    # Ola B · realtime: el cliente ve aparecer el check-in al instante en su
    # portal (antes solo al refrescar). SSE SIEMPRE después del commit (Pattern
    # #14 · admin-origin · cliente-facing).
    try:
        await sse_dispatcher.dispatch(
            f"project:{r.project_id}",
            "retainer.checkin.sent",
            {
                "primary_actor": "admin",
                "report_id": str(r.id),
                "period_quarter": r.period_quarter,
            },
        )
    except Exception:  # pragma: no cover · best-effort
        logger.warning("SSE retainer.checkin.sent dispatch failed (best-effort)")

    return _to_out(r)


@router.post("/reports/{report_id}/send", response_model=CheckinReportOut)
async def send_report(
    report_id: uuid.UUID,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> CheckinReportOut:
    """Marcos envía el check-in curado al cliente · curated_by_admin → sent_to_client."""
    await _set_rls_for_report(db, report_id)
    try:
        r = await RetainerCheckinService(db).admin_send_to_client(
            report_id, owner.id,
        )
    except CheckinReportNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidWorkflowTransitionError as exc:
        raise HTTPException(409, str(exc)) from exc
    await db.commit()
    return _to_out(r)
