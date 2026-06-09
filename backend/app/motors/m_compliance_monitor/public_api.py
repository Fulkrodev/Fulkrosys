"""Public-facing legal/compliance endpoints (atom 9.bis.5).

These endpoints are served WITHOUT authentication. They are consumed by:
- ``/(legal)/trust`` page (Trust Center)
- ``/(legal)/sub-processors`` page

The data is intentionally non-sensitive: aggregated compliance health,
list of frameworks, sub-processor count. No cliente data, no internal
control names — only the public-facing claims.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.compliance_monitor import (
    ComplianceCheck,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_UNKNOWN,
    STATUS_YELLOW,
)
from backend.app.motors.m_compliance_monitor.sub_processor_subscribers import (
    SubProcessorSubscriber,
)


router = APIRouter(
    prefix="/legal",
    tags=["MB-9.bis atom 5 — Public Legal/Trust"],
)


# ── Schemas ────────────────────────────────────────────────────────────


class FrameworkStatus(BaseModel):
    name: str
    status: str  # active, aligned, preparedness, planned
    regulatory_basis: str | None = None
    since: str | None = None


class ISMSCertification(BaseModel):
    name: str
    status: str  # preparedness, certified, planned
    expected: str | None = None


class NormaScore(BaseModel):
    """Per-norma score snapshot surfaced to the public Trust Center."""

    norma_key: str
    norma_name: str
    score: float | None
    status: str  # green / yellow / red / unknown
    last_report: str | None  # ISO date or null
    regulatory_basis_url: str


class ComplianceStatusOut(BaseModel):
    overall_health: str
    last_check: datetime | None
    compliance_frameworks: list[FrameworkStatus]
    sub_processors_count: int
    last_breach_reported: str | None
    isms_certifications: list[ISMSCertification]
    monitor_summary: dict[str, int]
    compliance_scores_per_norma: list[NormaScore]


class SubProcessorSubscribeBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    consent: bool = Field(
        ..., description="User explicit consent to receive sub-processor updates"
    )


class SubProcessorSubscribeOut(BaseModel):
    subscribed: bool
    email: str
    message: str


# ── GET /legal/compliance/status ───────────────────────────────────────


# Authoritative public claim list. Sourced from atom 9.bis.4 documentation;
# updated by Marcos when new frameworks are added (e.g. when ISO 27001
# certification completes the body becomes "certified" with cert_id).
_FRAMEWORKS_DECLARED: list[FrameworkStatus] = [
    FrameworkStatus(
        name="RGPD UE 2016/679",
        status="active",
        regulatory_basis="Regulamento (UE) 2016/679",
    ),
    FrameworkStatus(
        name="LOPDGDD 3/2018",
        status="active",
        regulatory_basis="Ley Orgánica 3/2018, de 5 de diciembre",
    ),
    FrameworkStatus(
        name="LSSI-CE 34/2002",
        status="active",
        regulatory_basis="Ley 34/2002, de 11 de julio",
    ),
    FrameworkStatus(
        name="NIS2 UE 2022/2555",
        status="aligned",
        regulatory_basis="Directiva (UE) 2022/2555",
    ),
    FrameworkStatus(
        name="Guía AEPD Cookies 2020",
        status="active",
        regulatory_basis="AEPD Guía sobre el uso de cookies",
    ),
    FrameworkStatus(
        name="ENS RD 311/2022",
        status="active",
        regulatory_basis="Real Decreto 311/2022, de 3 de mayo",
    ),
]

_ISMS_CERTIFICATIONS: list[ISMSCertification] = [
    ISMSCertification(
        name="ISO 27001:2022",
        status="preparedness",
        expected="Q4 2027",
    ),
    ISMSCertification(
        name="ISO 27701:2019",
        status="planned",
        expected="2028",
    ),
]

# Total declared in atom 9.bis.4 sub-processors MD + persisted in
# fulkro_ropa_treatments (atom 9.bis.3). The status endpoint reads the
# table when present; falls back to this constant otherwise so the page
# never returns 0 before that atom lands.
_FALLBACK_SUB_PROCESSORS_COUNT = 5


@router.get("/compliance/status", response_model=ComplianceStatusOut)
async def get_public_compliance_status(
    db: AsyncSession = Depends(get_db),
) -> ComplianceStatusOut:
    """Public live status snapshot consumed by the Trust Center."""

    counts_row = await db.execute(
        select(ComplianceCheck.status, func.count(ComplianceCheck.id)).group_by(
            ComplianceCheck.status
        )
    )
    counts = {s: c for s, c in counts_row.all()}
    red = counts.get(STATUS_RED, 0)
    yellow = counts.get(STATUS_YELLOW, 0)
    unknown = counts.get(STATUS_UNKNOWN, 0)
    green = counts.get(STATUS_GREEN, 0)
    total = red + yellow + unknown + green
    overall = (
        STATUS_RED if red > 0
        else STATUS_YELLOW if (yellow > 0 or unknown > 0)
        else STATUS_GREEN if total > 0
        else STATUS_UNKNOWN
    )

    last_check = (
        await db.execute(select(func.max(ComplianceCheck.last_run_at)))
    ).scalar()

    # Sub-processor count: prefer fulkro_ropa_treatments if it exists
    # (atom 9.bis.3), else the constant declared in this module.
    try:
        from sqlalchemy import text as _text
        row = await db.execute(
            _text(
                """
                SELECT COUNT(*)
                FROM fulkro_ropa_treatments
                WHERE is_sub_processor = true
                """
            )
        )
        sub_count = row.scalar() or _FALLBACK_SUB_PROCESSORS_COUNT
    except Exception:  # noqa: BLE001 — table absent → fallback
        sub_count = _FALLBACK_SUB_PROCESSORS_COUNT

    # Last breach: read fulkro_breach_notifications (created in atom
    # 9.bis.2). Only surface a date for breaches that have actually been
    # reported to the AEPD or closed — pending/unverified entries are
    # internal-only.
    try:
        from sqlalchemy import text as _text
        row = await db.execute(
            _text(
                """
                SELECT MAX(reported_at)
                FROM fulkro_breach_notifications
                WHERE notification_status IN (
                    'aepd_notified', 'clients_notified', 'closed_resolved'
                )
                """
            )
        )
        last_breach = row.scalar()
        last_breach_str = last_breach.isoformat() if last_breach else None
    except Exception:  # noqa: BLE001 — table absent → null
        last_breach_str = None

    # MB-9.bis mini-atom 3 · live per-norma scores from the plugin
    # registry + latest persisted report (if any).
    norma_scores: list[NormaScore] = []
    try:
        from backend.app.motors.m_compliance_monitor.norma_reports_service import (
            ComplianceNormaReportsService,
        )
        from backend.app.motors.m_compliance_monitor.normas import NormaRegistry

        latest = await ComplianceNormaReportsService(db).latest_per_norma()
        for module in NormaRegistry.get_all():
            row = latest.get(module.norma_key)
            norma_scores.append(
                NormaScore(
                    norma_key=module.norma_key,
                    norma_name=module.norma_name,
                    score=float(row.compliance_score) if row else None,
                    status=row.status if row else "unknown",
                    last_report=(
                        row.generated_at.date().isoformat() if row else None
                    ),
                    regulatory_basis_url=module.regulatory_basis_url,
                )
            )
    except Exception:  # noqa: BLE001
        norma_scores = []

    return ComplianceStatusOut(
        overall_health=overall,
        last_check=last_check,
        compliance_frameworks=_FRAMEWORKS_DECLARED,
        sub_processors_count=sub_count,
        last_breach_reported=last_breach_str,
        isms_certifications=_ISMS_CERTIFICATIONS,
        monitor_summary={
            "green": green,
            "yellow": yellow,
            "red": red,
            "unknown": unknown,
            "total": total,
        },
        compliance_scores_per_norma=norma_scores,
    )


# ── POST /legal/sub-processor-notifications/subscribe ──────────────────


_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post(
    "/sub-processor-notifications/subscribe",
    response_model=SubProcessorSubscribeOut,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe_sub_processor_updates(
    body: SubProcessorSubscribeBody,
    db: AsyncSession = Depends(get_db),
) -> SubProcessorSubscribeOut:
    """Subscribe an email to receive notifications when the sub-processor
    list changes (Art. 28.2 GDPR transparency obligation).

    Idempotent: re-subscribing the same email returns the same row with
    ``subscribed=true`` (no duplicate insert, no email enumeration).
    """
    email = str(body.email).strip().lower()
    if not _EMAIL_REGEX.match(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format",
        )
    if not body.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent required to subscribe",
        )

    existing = (
        await db.execute(
            select(SubProcessorSubscriber).where(
                SubProcessorSubscriber.email == email
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        row = SubProcessorSubscriber(
            email=email,
            consent_given_at=datetime.now(timezone.utc),
        )
        db.add(row)
        await db.flush()
        await db.commit()
    else:
        # Re-confirm consent (refresh timestamp without re-emailing).
        existing.consent_given_at = datetime.now(timezone.utc)
        existing.unsubscribed_at = None
        await db.flush()
        await db.commit()

    return SubProcessorSubscribeOut(
        subscribed=True,
        email=email,
        message=(
            "Suscripción registrada. Recibirás un email cuando la lista de "
            "sub-procesadores cambie (Art. 28.2 RGPD)."
        ),
    )
