"""Celery tasks RetainerChurnPredictor MB-18.4 (ADR-040).

Tasks expuestas:

1. ``retainer.scan_churn_risk`` · scan weekly Monday 09:30 Europe/Madrid ·
   compute ``RetainerHealthSignal`` per retainer active · alert
   AlertService category=``retainer_overdue`` (existing _VALID_CATEGORIES)
   si critical.

Stub-friendly: si Celery no instalado (dev/tests), decorador
``@celery_app.task`` actúa como identity (ver
``backend/app/core/celery_app.py``). Tasks pueden invocarse direct
síncronamente desde tests vía ``await scan_churn_risk_async()``.
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger
from sqlalchemy import text

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session
from backend.app.motors.m18_communication.alert_service import AlertService
from backend.app.notifications.deep_links import DeepLinkGenerator
from backend.app.retainer.churn_predictor import ChurnPredictor


def _ensure_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@celery_app.task(name="retainer.scan_churn_risk")
def scan_churn_risk() -> dict[str, Any]:
    """Scan weekly · compute churn signal + alert si critical."""
    logger.info("retainer.scan_churn_risk task triggered")
    loop = _ensure_loop()
    return loop.run_until_complete(scan_churn_risk_async())


async def scan_churn_risk_async() -> dict[str, Any]:
    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            stats = await scan_churn_risk_with_session(db)
            await db.commit()
            return stats
        except Exception:
            await db.rollback()
            raise


async def scan_churn_risk_with_session(db) -> dict[str, Any]:
    """Núcleo testeable · acepta session existente.

    Caller responsable SET LOCAL ROLE fulkro_app_bypassrls + commit/rollback.
    """
    predictor = ChurnPredictor(db)
    deep_links = DeepLinkGenerator()

    stats: dict[str, Any] = {
        "total_scanned": 0,
        "computed_count": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "alerts_created": 0,
        "errors": [],
    }

    signals = await predictor.scan_active_retainers()
    stats["total_scanned"] = len(signals)
    stats["computed_count"] = len(signals)

    alerts = AlertService(db)
    for signal in signals:
        level = signal.risk_level
        stats[f"{level}_count"] = stats.get(f"{level}_count", 0) + 1

        if level not in ("critical", "high"):
            continue
        try:
            severity = "critical" if level == "critical" else "warning"
            title = (
                f"Churn risk {level} · score {signal.churn_risk_score} · "
                f"retainer {signal.retainer_id}"
            )
            description = (
                signal.recommended_action or
                "Revisar retainer y planear intervención"
            )
            await db.execute(
                text(
                    "SELECT set_config('app.current_project_id', "
                    ":pid, true)"
                ),
                {"pid": str(signal.project_id)},
            )
            await alerts.trigger_alert(
                project_id=signal.project_id,
                severity=severity,
                category="retainer_overdue",
                title=title,
                description=description,
                action_url=deep_links._build(
                    "/admin/retainers/churn-risk"
                ),
                triggered_by="retainer.scan_churn_risk",
                metadata={
                    "retainer_id": str(signal.retainer_id),
                    "score": str(signal.churn_risk_score),
                    "risk_level": level,
                    "factors": signal.primary_risk_factors,
                },
            )
            stats["alerts_created"] += 1
        except Exception as exc:  # pragma: no cover · best effort
            logger.exception(
                "alert churn create failed retainer=%s",
                signal.retainer_id,
            )
            stats["errors"].append(f"alert:{signal.retainer_id}:{exc}")

    logger.info(
        "scan_churn_risk done · scanned={} critical={} high={} alerts={}",
        stats["total_scanned"],
        stats["critical_count"],
        stats["high_count"],
        stats["alerts_created"],
    )
    return stats


__all__ = [
    "scan_churn_risk",
    "scan_churn_risk_async",
    "scan_churn_risk_with_session",
]
