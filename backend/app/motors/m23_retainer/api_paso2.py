"""M23 Sesion 8 Paso 2 — Endpoints nuevos para dashboard K.6 y agente 26.

Se enganchan al router principal de M23 en api.py (include).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.core import Client
from backend.app.models.retainer import (
    PricingCatalog, RetainerActivity, RetainerContract,
)
from backend.app.motors.m23_retainer import agent_26, paso2_extensions
from backend.app.auth.dependencies import require_owner


router = APIRouter(
    prefix="/retainer/paso2", tags=["Motor 23 - Retainer Paso 2"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════

class SuggestTierBody(BaseModel):
    categoria: str = Field(..., pattern=r"^(BASICA|MEDIA|ALTA)$")
    empleados: int = Field(..., ge=1)
    sector: Optional[str] = None
    ubicaciones: int = Field(default=1, ge=1)
    datos_sensibles: bool = False


class MaterialChangeBody(BaseModel):
    change_description: str = Field(..., min_length=10, max_length=500)
    urgent: bool = False


class PricingCatalogEntry(BaseModel):
    category: str
    tier_code: str
    name: str
    base_price: float
    currency: str
    billing_unit: str
    extras_jsonb: dict[str, Any] | None = None
    description: str | None = None


# ════════════════════════════════════════════════════════════════════
# Dashboard K.6 multi-cliente
# ════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def retainers_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resumen multi-cliente de retainers activos.

    Vista bypass RLS (Marcos ve todos sus clientes). El endpoint
    ejecuta SET LOCAL ROLE fulkro_app_bypassrls internamente.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(RetainerContract).where(
            RetainerContract.estado == "active",
            RetainerContract.deleted_at.is_(None),
        )
    )
    retainers = list(r.scalars().all())

    client_names: dict[uuid.UUID, str] = {}
    if retainers:
        cids = {rc.client_id for rc in retainers}
        r = await db.execute(
            select(Client.id, Client.nombre).where(Client.id.in_(cids))
        )
        client_names = {row[0]: row[1] for row in r.all()}

    today = date.today()
    out: list[dict[str, Any]] = []
    mrr_total = 0.0
    for rc in retainers:
        # Next activity
        ra = (await db.execute(
            select(RetainerActivity).where(
                RetainerActivity.retainer_contract_id == rc.id,
                RetainerActivity.estado.in_(["programada", "en_curso"]),
                RetainerActivity.fecha_programada >= today,
                RetainerActivity.deleted_at.is_(None),
            ).order_by(RetainerActivity.fecha_programada.asc()).limit(1)
        )).scalar_one_or_none()
        next_act = None
        if ra:
            days = (ra.fecha_programada - today).days if ra.fecha_programada else None
            next_act = {
                "tipo": ra.tipo_actividad,
                "titulo": ra.titulo,
                "fecha": ra.fecha_programada.isoformat() if ra.fecha_programada else None,
                "countdown_days": days,
            }

        health = await paso2_extensions.calculate_health_status(db, rc.id)
        days_renewal = None
        if rc.next_renewal_date:
            days_renewal = (rc.next_renewal_date - today).days

        mrr_total += float(rc.precio_mensual or 0)
        out.append({
            "retainer_id": str(rc.id),
            "client_id": str(rc.client_id),
            "client_name": client_names.get(rc.client_id, "Cliente"),
            "tier": rc.perfil,
            "monthly_fee": float(rc.precio_mensual or 0),
            "health_status": health["health"],
            "rag_status_db": rc.rag_status,
            "next_activity": next_act,
            "cert_renewal_date": (
                rc.next_renewal_date.isoformat()
                if rc.next_renewal_date else None
            ),
            "days_until_renewal": days_renewal,
            "renewal_status": rc.renewal_status,
        })

    # Alertas agente 26
    agent_summary = await agent_26.summary_for_marcos(db)

    return {
        "retainers": out,
        "mrr_total": round(mrr_total, 2),
        "total_retainers": len(out),
        "agent_26_summary": agent_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{retainer_id}/timeline")
async def retainer_timeline(
    retainer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Calendario completo de actividades del retainer (iCal-like)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_id)
    if rc is None:
        raise HTTPException(status_code=404, detail="Retainer no encontrado")

    r = await db.execute(
        select(RetainerActivity).where(
            RetainerActivity.retainer_contract_id == retainer_id,
            RetainerActivity.deleted_at.is_(None),
        ).order_by(RetainerActivity.fecha_programada.asc())
    )
    events = []
    for a in r.scalars().all():
        events.append({
            "uid": str(a.id),
            "summary": a.titulo or a.tipo_actividad or "Actividad retainer",
            "description": a.descripcion or "",
            "dtstart": a.fecha_programada.isoformat() if a.fecha_programada else None,
            "status": a.estado,
            "priority": a.prioridad,
            "categories": [a.tipo_actividad] if a.tipo_actividad else [],
            "horas_estimadas": float(a.horas_estimadas or 0),
        })
    return {
        "retainer_id": str(retainer_id),
        "tier": rc.perfil,
        "events": events,
        "total_events": len(events),
    }


@router.get("/{retainer_id}/health-detail")
async def retainer_health_detail(
    retainer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_id)
    if rc is None:
        raise HTTPException(status_code=404, detail="Retainer no encontrado")
    return await paso2_extensions.calculate_health_status(db, retainer_id)


# ════════════════════════════════════════════════════════════════════
# Acciones
# ════════════════════════════════════════════════════════════════════

@router.post("/suggest-tier")
async def suggest_tier_endpoint(body: SuggestTierBody) -> dict[str, Any]:
    return paso2_extensions.suggest_tier(
        categoria=body.categoria,
        empleados=body.empleados,
        sector=body.sector,
        ubicaciones=body.ubicaciones,
        datos_sensibles=body.datos_sensibles,
    )


@router.post("/{retainer_id}/upgrade")
async def upgrade_tier(
    retainer_id: uuid.UUID,
    new_tier: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if new_tier not in ("R_MICRO", "R_LITE", "R_STD", "R_PLUS", "R_CRITICAL"):
        raise HTTPException(status_code=422, detail=f"Tier invalido: {new_tier}")
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_id)
    if rc is None:
        raise HTTPException(status_code=404, detail="Retainer no encontrado")
    new_price = await paso2_extensions.get_tier_price(db, new_tier)
    old = {"tier": rc.perfil, "price": float(rc.precio_mensual or 0)}
    rc.perfil = new_tier
    if new_price is not None:
        rc.precio_mensual = float(new_price)
    await db.flush()
    await db.commit()
    return {
        "retainer_id": str(retainer_id),
        "upgraded_from": old,
        "upgraded_to": {
            "tier": rc.perfil, "price": float(rc.precio_mensual or 0),
        },
    }


@router.post("/material-change/{project_id}")
async def material_change(
    project_id: uuid.UUID,
    body: MaterialChangeBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    activity = await paso2_extensions.trigger_material_change_audit(
        db, project_id, body.change_description, urgent=body.urgent,
    )
    await db.commit()
    return {
        "activity_id": str(activity.id),
        "fecha_programada": (
            activity.fecha_programada.isoformat()
            if activity.fecha_programada else None
        ),
        "titulo": activity.titulo,
    }


@router.get("/pricing-catalog")
async def get_pricing_catalog(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> list[PricingCatalogEntry]:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    stmt = select(PricingCatalog).where(
        PricingCatalog.is_active.is_(True),
        PricingCatalog.deleted_at.is_(None),
    )
    if category:
        stmt = stmt.where(PricingCatalog.category == category)
    r = await db.execute(stmt.order_by(PricingCatalog.category, PricingCatalog.base_price))
    return [
        PricingCatalogEntry(
            category=row.category,
            tier_code=row.tier_code,
            name=row.name,
            base_price=float(row.base_price),
            currency=row.currency,
            billing_unit=row.billing_unit,
            extras_jsonb=row.extras_jsonb or {},
            description=row.description,
        )
        for row in r.scalars().all()
    ]


@router.get("/agent-26/summary")
async def agent_26_summary(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await agent_26.summary_for_marcos(db)


@router.get("/agent-26/alerts")
async def agent_26_alerts(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    alerts = await agent_26.run_weekly_analysis(db)
    return [a.to_dict() for a in alerts]


__all__ = ["router"]
