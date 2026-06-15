"""M27 Renewal Extensions · timeline + contact-auditor + auditor-info.

ADR-046 v3 SAN-E.MB-3.D · 3 endpoints NEW project-scoped (paths flat
para alinear con frontend, NO bajo /conformity).

Endpoints:
    GET  /api/v1/projects/{id}/renewal/timeline
    POST /api/v1/projects/{id}/renewal/contact-auditor
    GET  /api/v1/projects/{id}/renewal/auditor-info
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import CurrentUser, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.conformity_lifecycle import RenewalCampaignRow
from backend.app.models.m27_renewal_milestone import (
    DEFAULT_MILESTONES,
    RenewalCampaignMilestone,
)


router = APIRouter(
    prefix="/projects/{project_id}/renewal",
    tags=["Motor 27 - Renewal Extensions"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _get_active_campaign(
    project_id: uuid.UUID, db: AsyncSession,
) -> RenewalCampaignRow | None:
    """Lectura pura (§2.5): NO crea nada · None si no hay campaign."""
    return (await db.execute(
        select(RenewalCampaignRow).where(
            RenewalCampaignRow.project_id == project_id,
        ).order_by(RenewalCampaignRow.created_at.desc())
    )).scalars().first()


def _ephemeral_timeline(
    project_id: uuid.UUID, campaign: RenewalCampaignRow | None = None,
) -> dict[str, Any]:
    """Timeline por defecto CALCULADO (no persistido · §2.5) para la vista cuando
    aún no hay campaign/milestones materializados. La materialización ocurre en la
    acción POST (contact-auditor) o el scheduler de renovación, NO en un GET."""
    scheduled = (
        campaign.scheduled_for if campaign and campaign.scheduled_for
        else datetime.now(timezone.utc) + timedelta(weeks=24)
    )
    ms = [
        {
            "id": None,
            "campaign_id": str(campaign.id) if campaign else None,
            "milestone_code": entry["code"],
            "label": entry["label"],
            "due_date": (scheduled + timedelta(weeks=entry["offset_weeks"])).isoformat(),
            "status": "pendiente",
            "responsable": None,
            "completed_at": None,
            "notes": None,
        }
        for entry in DEFAULT_MILESTONES
    ]
    return {
        "project_id": str(project_id),
        "campaign_id": str(campaign.id) if campaign else None,
        "campaign_type": campaign.campaign_type if campaign else "recertification_bianual",
        "scheduled_for": scheduled.isoformat(),
        "milestones": ms,
        "progress": {"total": len(ms), "completed": 0, "completed_pct": 0.0},
        "ephemeral": True,
    }


async def _get_or_create_active_campaign(
    project_id: uuid.UUID, db: AsyncSession,
) -> RenewalCampaignRow:
    row = await _get_active_campaign(project_id, db)
    if row is not None:
        return row
    # Crear placeholder campaign si no hay ninguna · scheduled 6 meses adelante
    campaign = RenewalCampaignRow(
        project_id=project_id,
        campaign_type="recertification_bianual",
        scheduled_for=datetime.now(timezone.utc) + timedelta(weeks=24),
        auto_triggered=False,
        status="planned",
    )
    db.add(campaign)
    await db.flush()
    return campaign


async def _seed_default_milestones(
    campaign: RenewalCampaignRow, db: AsyncSession,
) -> list[RenewalCampaignMilestone]:
    """Seed lazy 8 milestones default si la campaign no tiene aun."""
    existing = (await db.execute(
        select(RenewalCampaignMilestone).where(
            RenewalCampaignMilestone.campaign_id == campaign.id,
            RenewalCampaignMilestone.deleted_at.is_(None),
        )
    )).scalars().all()
    if existing:
        return existing
    audit_date = campaign.scheduled_for or (datetime.now(timezone.utc) + timedelta(weeks=24))
    milestones: list[RenewalCampaignMilestone] = []
    for entry in DEFAULT_MILESTONES:
        ms = RenewalCampaignMilestone(
            campaign_id=campaign.id,
            milestone_code=entry["code"],
            label=entry["label"],
            due_date=audit_date + timedelta(weeks=entry["offset_weeks"]),
            status="pendiente",
        )
        db.add(ms)
        milestones.append(ms)
    await db.flush()
    return milestones


def _milestone_to_dict(m: RenewalCampaignMilestone) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "campaign_id": str(m.campaign_id),
        "milestone_code": m.milestone_code,
        "label": m.label,
        "due_date": m.due_date.isoformat() if m.due_date else None,
        "status": m.status,
        "responsable": m.responsable,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        "notes": m.notes,
    }


@router.get("/timeline")
async def get_renewal_timeline(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    # §2.5 · GET read-only: NO crea campaign/milestones (eso es una acción · POST
    # contact-auditor o el scheduler). Sin campaign persistida → timeline efímero.
    campaign = await _get_active_campaign(project_id, db)
    if campaign is None:
        return _ephemeral_timeline(project_id)
    milestones = (await db.execute(
        select(RenewalCampaignMilestone).where(
            RenewalCampaignMilestone.campaign_id == campaign.id,
            RenewalCampaignMilestone.deleted_at.is_(None),
        )
    )).scalars().all()
    if not milestones:
        # campaign sin milestones materializados → preview efímero sobre su fecha
        return _ephemeral_timeline(project_id, campaign=campaign)
    sorted_ms = sorted(milestones, key=lambda m: (m.due_date or datetime.max.replace(tzinfo=timezone.utc)))
    completed = sum(1 for m in sorted_ms if m.status == "completado")
    return {
        "project_id": str(project_id),
        "campaign_id": str(campaign.id),
        "campaign_type": campaign.campaign_type,
        "scheduled_for": campaign.scheduled_for.isoformat() if campaign.scheduled_for else None,
        "milestones": [_milestone_to_dict(m) for m in sorted_ms],
        "progress": {
            "total": len(sorted_ms),
            "completed": completed,
            "completed_pct": round(100 * completed / len(sorted_ms), 1) if sorted_ms else 0.0,
        },
    }


class ContactAuditorBody(BaseModel):
    auditor_email: EmailStr
    auditor_name: str = Field(..., min_length=2, max_length=255)
    audit_entity: str | None = Field(None, max_length=255)
    message: str = Field(..., min_length=10, max_length=2000)


@router.post("/contact-auditor")
async def contact_auditor(
    project_id: uuid.UUID,
    body: ContactAuditorBody,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Outreach auditor ENAC · marca milestone auditor_contact + log intencion.

    Nota: integracion real con Postmark + magic_link ml_AUDITOR_ENAC_REVIEW
    se cablea en SAN-E.MB-7.X (post backend-extension). Aqui registra
    intencion + payload + completa milestone auditor_contact.
    """
    await _set_project_rls(project_id, db)
    campaign = await _get_or_create_active_campaign(project_id, db)
    await _seed_default_milestones(campaign, db)
    ms = (await db.execute(
        select(RenewalCampaignMilestone).where(
            RenewalCampaignMilestone.campaign_id == campaign.id,
            RenewalCampaignMilestone.milestone_code == "auditor_contact",
            RenewalCampaignMilestone.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if ms is None:
        raise HTTPException(status_code=500, detail="auditor_contact milestone missing")
    ms.status = "completado"
    ms.completed_at = datetime.now(timezone.utc)
    ms.responsable = str(user.id) if user else None
    ms.notes = (
        f"Outreach a {body.auditor_name} <{body.auditor_email}>"
        + (f" (entidad: {body.audit_entity})" if body.audit_entity else "")
        + f" · message: {body.message[:500]}"
    )
    await db.flush()
    await db.commit()
    return {
        "milestone_id": str(ms.id),
        "status": ms.status,
        "completed_at": ms.completed_at.isoformat(),
        "auditor_email": body.auditor_email,
        "next_step": "auditor recibira magic_link ml_AUDITOR_ENAC_REVIEW (cableado MB-7)",
    }


@router.get("/auditor-info")
async def get_auditor_info(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Info consolidada auditor + ventana auditoria activa."""
    await _set_project_rls(project_id, db)
    # §2.5 · GET read-only: sin campaign persistida → placeholder (sin escribir).
    campaign = await _get_active_campaign(project_id, db)
    if campaign is None:
        # §2.5 · read-only: ventana de auditoría CALCULADA (no persistida) para la
        # vista · la materialización ocurre en la acción POST / scheduler.
        scheduled = datetime.now(timezone.utc) + timedelta(weeks=24)
        aw = next(
            (e for e in DEFAULT_MILESTONES if e["code"] == "audit_window"), None,
        )
        return {
            "project_id": str(project_id),
            "campaign_id": None,
            "campaign_status": None,
            "audit_window_due": (
                (scheduled + timedelta(weeks=aw["offset_weeks"])).isoformat()
                if aw else None
            ),
            "auditor_contacted": False,
            "auditor_contacted_at": None,
            "auditor_contact_notes": None,
            "ephemeral": True,
        }
    auditor_contact_ms = (await db.execute(
        select(RenewalCampaignMilestone).where(
            RenewalCampaignMilestone.campaign_id == campaign.id,
            RenewalCampaignMilestone.milestone_code == "auditor_contact",
            RenewalCampaignMilestone.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    audit_window_ms = (await db.execute(
        select(RenewalCampaignMilestone).where(
            RenewalCampaignMilestone.campaign_id == campaign.id,
            RenewalCampaignMilestone.milestone_code == "audit_window",
            RenewalCampaignMilestone.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    return {
        "project_id": str(project_id),
        "campaign_id": str(campaign.id),
        "campaign_status": campaign.status,
        "audit_window_due": audit_window_ms.due_date.isoformat() if audit_window_ms and audit_window_ms.due_date else None,
        "auditor_contacted": auditor_contact_ms.status == "completado" if auditor_contact_ms else False,
        "auditor_contacted_at": (
            auditor_contact_ms.completed_at.isoformat()
            if auditor_contact_ms and auditor_contact_ms.completed_at
            else None
        ),
        "auditor_contact_notes": auditor_contact_ms.notes if auditor_contact_ms else None,
    }
