"""Admin System Health Aggregator · Bloque 4 Phase D v3.12.

Endpoint admin-only que aggregates self-monitoring FULKRO platform health:
  - m_compliance_monitor 19 checks latest status (last_status + last_run_at)
  - m_observability LLM anomaly alerts (best-effort · si infra disponible)
  - DB pool basic health (best-effort)

Reuse data existing m_compliance_monitor + m_observability · NO new scheduled
tasks (Celery beat existing handles 19 checks daily/weekly/monthly/quarterly).

R23 explicit · admin-only top-level (self-monitoring NO cliente concern · R29
sostained · cliente NO ve).
ADR-025 28a aplicacion sostained · NO new tables · query existing models.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.compliance_monitor import (
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW,
    ComplianceCheck,
)


HealthIndicator = Literal["ok", "warning", "critical", "unknown"]


router = APIRouter(
    prefix="/admin/system-health",
    tags=["Admin · System Health (Bloque 4)"],
    dependencies=[Depends(require_owner)],
)


# ──────────────────────────────────────────────────────────────────────
# Schemas


class CheckHealth(BaseModel):
    name: str
    description: str | None
    status: HealthIndicator
    last_run_at: str | None
    severity: str | None
    frequency: str | None


class SystemHealthResponse(BaseModel):
    generated_at: str
    overall_health: HealthIndicator
    counts: dict[str, int]
    compliance_checks: list[CheckHealth]
    llm_anomalies_count: int
    db_connection_ok: bool


# ──────────────────────────────────────────────────────────────────────
# Helpers


def _status_to_indicator(raw_status: str | None) -> HealthIndicator:
    """Map m_compliance_monitor status (green/yellow/red/unknown) → HealthIndicator."""
    if raw_status == STATUS_GREEN:
        return "ok"
    if raw_status == STATUS_YELLOW:
        return "warning"
    if raw_status == STATUS_RED:
        return "critical"
    return "unknown"


def _overall_from_indicators(indicators: list[HealthIndicator]) -> HealthIndicator:
    if "critical" in indicators:
        return "critical"
    if "warning" in indicators:
        return "warning"
    if "unknown" in indicators and "ok" not in indicators:
        return "unknown"
    return "ok"


# ──────────────────────────────────────────────────────────────────────
# Endpoint


@router.get("", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
) -> SystemHealthResponse:
    """Aggregated system health · 19 compliance checks + LLM anomalies + DB."""

    # 1. Compliance checks (m_compliance_monitor)
    try:
        result = await db.execute(
            select(ComplianceCheck).order_by(ComplianceCheck.name.asc())
        )
        checks_rows = list(result.scalars().all())
    except Exception:  # noqa: BLE001
        checks_rows = []

    compliance_checks: list[CheckHealth] = []
    counts = {"ok": 0, "warning": 0, "critical": 0, "unknown": 0}
    indicators: list[HealthIndicator] = []

    for c in checks_rows:
        indicator = _status_to_indicator(getattr(c, "last_status", None))
        counts[indicator] = counts.get(indicator, 0) + 1
        indicators.append(indicator)
        compliance_checks.append(CheckHealth(
            name=c.name,
            description=getattr(c, "description", None),
            status=indicator,
            last_run_at=(
                c.last_run_at.isoformat()
                if getattr(c, "last_run_at", None) else None
            ),
            severity=getattr(c, "severity", None),
            frequency=getattr(c, "frequency", None),
        ))

    # 2. LLM anomalies count (m_observability best-effort)
    llm_anomalies_count = 0
    try:
        from backend.app.motors.m_observability.llm_observability_service import (
            get_anomaly_alerts,
        )
        alerts = await get_anomaly_alerts(db) or []
        llm_anomalies_count = len(alerts) if isinstance(alerts, list) else 0
    except Exception:  # noqa: BLE001
        llm_anomalies_count = 0

    if llm_anomalies_count > 0:
        indicators.append("warning")
        counts["warning"] = counts.get("warning", 0) + 1

    # 3. DB connection basic health (best-effort)
    db_connection_ok = True
    try:
        await db.execute(select(1))
    except Exception:  # noqa: BLE001
        db_connection_ok = False
        indicators.append("critical")

    overall = _overall_from_indicators(indicators) if indicators else "unknown"

    return SystemHealthResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        overall_health=overall,
        counts=counts,
        compliance_checks=compliance_checks,
        llm_anomalies_count=llm_anomalies_count,
        db_connection_ok=db_connection_ok,
    )
