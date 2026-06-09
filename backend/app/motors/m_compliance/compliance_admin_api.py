"""Admin endpoints for erasure review + breach notification (atom 9.bis.2).

Endpoints under ``/api/v1/admin/compliance``:

- /erasure-requests           — list pending requests
- /erasure-requests/{id}/approve   — execute tombstone anonymisation + notify
- /erasure-requests/{id}/reject    — refuse on legal-retention basis + notify
- /breach                     — list all breaches
- /breach/register            — create a new breach record
- /breach/{id}/notify-aepd    — send Art. 33 notification email
- /breach/{id}/notify-clients — send Art. 34 notifications to affected
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.email.sender import get_email_sender
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.client_portal import ClientUser
from backend.app.models.compliance_breach_erasure import (
    FulkroBreachNotification,
    FulkroErasureRequest,
)
from backend.app.motors.m_compliance.breach_service import (
    BreachNotificationService,
)
from backend.app.motors.m_compliance.rgpd_services import RGPDErasureService


router = APIRouter(
    prefix="/admin/compliance",
    tags=["MB-9.bis atom 2 — Admin RGPD + Breach"],
    dependencies=[Depends(require_owner)],
)


# ── Schemas ────────────────────────────────────────────────────────────


class ErasureRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_user_id: UUID
    requested_at: datetime
    requester_reason: str | None
    status: str
    processed_at: datetime | None
    processed_by: str | None
    rejection_reason: str | None


class ErasureRejectBody(BaseModel):
    rejection_reason: str | None = Field(default=None, max_length=2000)


class BreachRegisterBody(BaseModel):
    detected_at: datetime
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    description: str = Field(min_length=10, max_length=10000)
    data_categories_affected: list[str] = Field(min_length=1)
    data_subjects_count: int | None = Field(default=None, ge=0)
    root_cause: str | None = None
    containment_actions: str | None = None
    remediation_actions: str | None = None
    affected_client_user_ids: list[UUID] | None = None


class BreachOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    breach_code: str
    detected_at: datetime
    reported_at: datetime | None
    severity: str
    description: str
    data_categories_affected: list[str]
    data_subjects_count: int | None
    notification_status: str
    notified_aepd_at: datetime | None
    notified_clients_at: datetime | None
    aepd_reference: str | None


class BreachNotifyClientsOut(BaseModel):
    breach: BreachOut
    emails_sent: int


# ── Erasure: list + approve + reject ──────────────────────────────────


@router.get("/erasure-requests", response_model=list[ErasureRequestOut])
async def list_erasure_requests(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ErasureRequestOut]:
    stmt = select(FulkroErasureRequest).order_by(
        desc(FulkroErasureRequest.requested_at)
    )
    if status_filter:
        stmt = stmt.where(FulkroErasureRequest.status == status_filter)
    rows = (await db.execute(stmt)).scalars().all()
    return [ErasureRequestOut.model_validate(r) for r in rows]


@router.post(
    "/erasure-requests/{request_id}/approve",
    response_model=ErasureRequestOut,
)
async def approve_erasure(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> ErasureRequestOut:
    svc = RGPDErasureService(db)
    # Capture cliente email BEFORE anonymisation so we can email them.
    req_row = (
        await db.execute(
            select(FulkroErasureRequest).where(
                FulkroErasureRequest.id == request_id
            )
        )
    ).scalar_one_or_none()
    if req_row is None:
        raise HTTPException(404, detail="ErasureRequest not found")
    cliente = (
        await db.execute(
            select(ClientUser).where(ClientUser.id == req_row.client_user_id)
        )
    ).scalar_one_or_none()
    cliente_email = cliente.email if cliente else None

    try:
        completed = await svc.approve_and_anonymise(
            request_id, processed_by=user.email or str(user.id)
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    await db.commit()

    if cliente_email and not cliente_email.startswith("anonymised_"):
        await _send_erasure_email(
            db, cliente_email, "erasure_completed.html", completed
        )

    return ErasureRequestOut.model_validate(completed)


@router.post(
    "/erasure-requests/{request_id}/reject",
    response_model=ErasureRequestOut,
)
async def reject_erasure(
    request_id: UUID,
    body: ErasureRejectBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> ErasureRequestOut:
    svc = RGPDErasureService(db)
    req_row = (
        await db.execute(
            select(FulkroErasureRequest).where(
                FulkroErasureRequest.id == request_id
            )
        )
    ).scalar_one_or_none()
    if req_row is None:
        raise HTTPException(404, detail="ErasureRequest not found")
    cliente = (
        await db.execute(
            select(ClientUser).where(ClientUser.id == req_row.client_user_id)
        )
    ).scalar_one_or_none()
    cliente_email = cliente.email if cliente else None

    rejected = await svc.reject_audit_retention(
        request_id,
        processed_by=user.email or str(user.id),
        rejection_reason=body.rejection_reason,
    )
    await db.commit()

    if cliente_email:
        await _send_erasure_email(
            db, cliente_email, "erasure_rejected.html", rejected
        )

    return ErasureRequestOut.model_validate(rejected)


# ── Breach: list + register + notify aepd + notify clients ───────────


@router.get("/breach", response_model=list[BreachOut])
async def list_breaches(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[BreachOut]:
    stmt = select(FulkroBreachNotification).order_by(
        desc(FulkroBreachNotification.detected_at)
    )
    if status_filter:
        stmt = stmt.where(
            FulkroBreachNotification.notification_status == status_filter
        )
    rows = (await db.execute(stmt)).scalars().all()
    return [BreachOut.model_validate(r) for r in rows]


@router.post(
    "/breach/register",
    response_model=BreachOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_breach(
    body: BreachRegisterBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> BreachOut:
    svc = BreachNotificationService(db)
    row = await svc.register_breach(
        detected_at=body.detected_at,
        severity=body.severity,
        description=body.description,
        data_categories_affected=body.data_categories_affected,
        data_subjects_count=body.data_subjects_count,
        root_cause=body.root_cause,
        containment_actions=body.containment_actions,
        affected_client_user_ids=body.affected_client_user_ids,
        reporter_user_id=user.id,
    )
    if body.remediation_actions:
        row.remediation_actions = body.remediation_actions
        await db.flush()
    await db.commit()
    return BreachOut.model_validate(row)


@router.post("/breach/{breach_id}/notify-aepd", response_model=BreachOut)
async def notify_aepd(
    breach_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> BreachOut:
    svc = BreachNotificationService(db)
    try:
        row = await svc.notify_aepd(breach_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    await db.commit()
    return BreachOut.model_validate(row)


@router.post(
    "/breach/{breach_id}/notify-clients",
    response_model=BreachNotifyClientsOut,
)
async def notify_clients(
    breach_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> BreachNotifyClientsOut:
    svc = BreachNotificationService(db)
    try:
        row, sent = await svc.notify_affected_clients(breach_id)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    await db.commit()
    return BreachNotifyClientsOut(
        breach=BreachOut.model_validate(row),
        emails_sent=sent,
    )


# ── Helpers ─────────────────────────────────────────────────────────


async def _send_erasure_email(
    db: AsyncSession,
    cliente_email: str,
    template_name: str,
    request: FulkroErasureRequest,
) -> None:
    """Render + send the erasure-state email (best effort)."""
    # Translate legacy .html template name to the MJML equivalent so older
    # call sites continue to work.
    mjml_name = template_name.replace(".html", ".mjml")
    from backend.app.motors.m_compliance.email_design.mjml_compiler import (
        render_email as render_mjml_email,
    )
    html = render_mjml_email(mjml_name, dict(request=request))
    subject = (
        "[FULKRO] Solicitud de supresión "
        + ("completada" if "completed" in template_name else "denegada")
    )
    try:
        await get_email_sender().send(
            db,
            to=cliente_email,
            subject=subject,
            html_body=html,
            template_used=mjml_name.replace(".mjml", ""),
        )
    except Exception:  # noqa: BLE001
        pass
