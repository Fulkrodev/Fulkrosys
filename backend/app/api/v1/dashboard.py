"""Admin Dashboard router · Marcos cockpit home · FASE 2 H4 wire-up real.

4 endpoints REST cross-motor aggregator (require_owner):
    GET /api/v1/dashboard/kpis     → DashboardKpis
    GET /api/v1/dashboard/my-day   → list[MyDayItem]
    GET /api/v1/dashboard/alerts   → list[DashboardAlert]
    GET /api/v1/dashboard/activity → list[ActivityEvent]

Distinct de:
- ``/api/v1/projects/{id}/dashboard`` (M21 per-project · ADR-035)
- ``/api/v1/client-portal/dashboard/adaptive`` (M21 cliente portal · Q5.2/Q5.3)
- ``/api/v1/retainer/dashboard`` (M23 retainer multi-cliente)

NO scope creep guided mode (ADR-050 cement defer MB-14).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.services.admin_dashboard_service import (
    ActivityEvent,
    AdminDashboardService,
    DashboardAlert,
    DashboardKpis,
    MyDayItem,
)

router = APIRouter(
    prefix="/dashboard",
    tags=["Admin Dashboard (Marcos cockpit)"],
    dependencies=[Depends(require_owner)],
)


@router.get(
    "/kpis",
    response_model=DashboardKpis,
    summary="KPIs cross-clients Marcos cockpit",
)
async def get_kpis(
    db: AsyncSession = Depends(get_db),
) -> DashboardKpis:
    """Aggregated KPIs cross-clients · header KpiRow admin home.

    Cross-motor sources:
    - active_projects: projects WHERE lifecycle_state NOT IN (ARCHIVED, PURGED)
    - leads_count + leads_value_eur: leads + proposals (M13)
    - retainers_active + mrr_eur: retainer_contracts (M23)
    - treasury_30d_eur + trend_pct: invoices SUM últimos 30d (M15)
    - projects_rag: worst-of-all retainers activos rag_status
    """
    service = AdminDashboardService(db)
    return await service.get_kpis()


@router.get(
    "/my-day",
    response_model=list[MyDayItem],
    summary="Today's Marcos tasks (review + signatures + meetings)",
)
async def get_my_day(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[MyDayItem]:
    """Items home Marcos · review docs + signatures + meetings today.

    Cross-motor:
    - review_docs: M06 documents WHERE approved_at IS NULL
    - signature: M14 contracts WHERE firmado_cliente_at NOT NULL AND firmado_marcos_at IS NULL
    - meeting: M_meetings exploratory_meetings WHERE meeting_date::date = today
    """
    service = AdminDashboardService(db)
    return await service.get_my_day(limit=limit)


@router.get(
    "/alerts",
    response_model=list[DashboardAlert],
    summary="Cross-motor alerts (compliance + drift)",
)
async def get_alerts(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[DashboardAlert]:
    """Cross-motor alerts agregados.

    Sources:
    - m_compliance_monitor.ComplianceAlert (status='open')
    - m23.RetainerDriftEvent (estado IN open/acknowledged)
    """
    service = AdminDashboardService(db)
    return await service.get_alerts(limit=limit)


@router.get(
    "/activity",
    response_model=list[ActivityEvent],
    summary="Recent activity feed (audit_log filtered)",
)
async def get_activity(
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityEvent]:
    """Recent activity events derivados desde audit_log.

    Tablas tracked: evidence · verification_runs · proposals · signing_intents ·
    contracts · signing_events · agent_runs.
    """
    service = AdminDashboardService(db)
    return await service.get_activity(limit=limit)
