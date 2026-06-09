"""Motor 23 · Retainer quarterly checkin portal cliente · MB-6 atom 4.

Trimestral uniforme · admin curate obligatorio · cliente review + firma.

Endpoints cliente:
- GET   /portal/retainer-checkin/projects/{id}                 · list visible
- GET   /portal/retainer-checkin/{id}                          · detail
- POST  /portal/retainer-checkin/{id}/review                   · review action
- GET   /portal/retainer-checkin/{id}/document-hash            · SHA256 pre-firma
- POST  /portal/retainer-checkin/{id}/finalize-signoff         · link signing_intent
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.models.retainer import RetainerQuarterlyReport
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m23_retainer.retainer_checkin_service import (
    CheckinAlreadySignedError,
    CheckinReportNotFoundError,
    InvalidReviewActionError,
    NoActiveRetainerError,
    RetainerCheckinError,
    RetainerCheckinService,
)


router = APIRouter(
    prefix="/portal/retainer-checkin",
    tags=["Motor 23 - Retainer checkin (cliente)"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class CheckinClientOut(BaseModel):
    """Vista cliente single quarterly checkin · admin_curation_status='sent_to_client'."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    period_quarter: str | None
    period_start: date
    period_end: date
    activities_completed: int
    activities_pending: int
    activities_overdue: int
    incidents_detected: int
    normativa_changes_relevant: int
    vulns_critical: int
    rag_overall: str | None
    admin_curation_status: str
    sent_at: datetime | None
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None
    summary_jsonb: dict | None
    schema_version: str
    created_at: datetime


class CheckinReviewRequest(BaseModel):
    action: str = Field(..., description="revisada_ok / con_pregunta / suggest_change")
    note: str | None = Field(None, max_length=4000)


class CheckinDocumentHashOut(BaseModel):
    report_id: uuid.UUID
    period_quarter: str | None
    canonical_length: int
    document_hash_sha256: str
    ready_for_signing: bool


class CheckinFinalizeSignoffRequest(BaseModel):
    signing_intent_id: uuid.UUID


class CheckinFinalizeSignoffOut(BaseModel):
    report_id: uuid.UUID
    signing_intent_id: uuid.UUID


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _service(db: AsyncSession) -> RetainerCheckinService:
    return RetainerCheckinService(db)


async def _ensure_project_belongs_to_client(
    db: AsyncSession, project_id: uuid.UUID, user: ClientUser,
) -> None:
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Project no existe")
    if hit[0] != user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(db, client_id=user.client_id, project_id=project_id)


async def _get_report_project(
    db: AsyncSession, report_id: uuid.UUID,
) -> uuid.UUID:
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text(
            "SELECT project_id FROM retainer_quarterly_reports WHERE id = :rid"
        ),
        {"rid": str(report_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Checkin report no existe")
    return hit[0]


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CheckinReportNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, NoActiveRetainerError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, InvalidReviewActionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, CheckinAlreadySignedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, RetainerCheckinError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _to_out(report: RetainerQuarterlyReport) -> CheckinClientOut:
    return CheckinClientOut(
        id=report.id,
        project_id=report.project_id,
        period_quarter=report.period_quarter,
        period_start=report.period_start,
        period_end=report.period_end,
        activities_completed=report.activities_completed,
        activities_pending=report.activities_pending,
        activities_overdue=report.activities_overdue,
        incidents_detected=report.incidents_detected,
        normativa_changes_relevant=report.normativa_changes_relevant,
        vulns_critical=report.vulns_critical,
        rag_overall=report.rag_overall,
        admin_curation_status=report.admin_curation_status,
        sent_at=report.sent_at,
        client_review_status=report.client_review_status,
        client_review_note=report.client_review_note,
        client_reviewed_at=report.client_reviewed_at,
        client_signing_intent_id=report.client_signing_intent_id,
        summary_jsonb=report.summary_jsonb,
        schema_version=report.schema_version,
        created_at=report.created_at,
    )


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}",
    response_model=list[CheckinClientOut],
)
async def list_client_checkins(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[CheckinClientOut]:
    """Lista quarterly checkins visible · admin_curation_status='sent_to_client'."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    reports = await _service(db).list_for_client(project_id)
    return [_to_out(r) for r in reports]


@router.get(
    "/{report_id}",
    response_model=CheckinClientOut,
)
async def get_client_checkin_detail(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> CheckinClientOut:
    """Detail single · enforce sent_to_client visibility."""
    project_id = await _get_report_project(db, report_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    report = await db.get(RetainerQuarterlyReport, report_id)
    if report is None or report.admin_curation_status != "sent_to_client":
        raise HTTPException(status_code=404, detail="Checkin no visible")
    return _to_out(report)


@router.post(
    "/{report_id}/review",
    response_model=CheckinClientOut,
)
async def review_checkin(
    report_id: uuid.UUID,
    body: CheckinReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> CheckinClientOut:
    """Cliente review action."""
    project_id = await _get_report_project(db, report_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        report = await _service(db).mark_client_review(
            report_id=report_id,
            action=body.action,
            note=body.note,
            user_id=user.id,
        )
    except (
        InvalidReviewActionError,
        CheckinReportNotFoundError,
        RetainerCheckinError,
    ) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()
    return _to_out(report)


@router.get(
    "/{report_id}/document-hash",
    response_model=CheckinDocumentHashOut,
)
async def get_checkin_hash(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> CheckinDocumentHashOut:
    """SHA256 canonical · pre-firma."""
    project_id = await _get_report_project(db, report_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        doc_hash, canonical_length = await _service(db).compute_signoff_hash(
            report_id,
        )
    except CheckinReportNotFoundError as exc:
        raise _handle_service_error(exc) from exc

    report = await db.get(RetainerQuarterlyReport, report_id)
    assert report is not None
    ready = (
        report.admin_curation_status == "sent_to_client"
        and report.client_reviewed_at is not None
        and report.client_signing_intent_id is None
    )

    return CheckinDocumentHashOut(
        report_id=report_id,
        period_quarter=report.period_quarter,
        canonical_length=canonical_length,
        document_hash_sha256=doc_hash,
        ready_for_signing=ready,
    )


@router.post(
    "/{report_id}/finalize-signoff",
    response_model=CheckinFinalizeSignoffOut,
)
async def finalize_checkin_signoff(
    report_id: uuid.UUID,
    body: CheckinFinalizeSignoffRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> CheckinFinalizeSignoffOut:
    """Post-firma · link signing_intent_id."""
    project_id = await _get_report_project(db, report_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    intent = await db.get(SigningIntent, body.signing_intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="SigningIntent no existe")
    if intent.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="SigningIntent no pertenece al project",
        )
    if intent.signable_type != "retainer_quarterly_signoff":
        raise HTTPException(
            status_code=400,
            detail=(
                f"SigningIntent.signable_type='{intent.signable_type}' "
                f"esperado 'retainer_quarterly_signoff'"
            ),
        )
    if intent.status != "signed":
        raise HTTPException(
            status_code=409,
            detail=f"SigningIntent status='{intent.status}' · esperado 'signed'",
        )

    try:
        report = await _service(db).process_quarterly_signoff(
            report_id=report_id,
            signing_intent_id=body.signing_intent_id,
        )
    except (CheckinReportNotFoundError, CheckinAlreadySignedError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    return CheckinFinalizeSignoffOut(
        report_id=report.id,
        signing_intent_id=body.signing_intent_id,
    )
