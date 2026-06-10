"""Celery tasks for the FULKRO Self-Monitoring System (atom 9.bis.6).

Beat schedule (registered in ``core/celery_app.py``):

- ``compliance.run_daily``     → daily 07:30 Europe/Madrid
- ``compliance.run_weekly``    → Monday 08:00 (after daily) — also generates report
- ``compliance.run_monthly``   → 1st of month 08:30
- ``compliance.run_quarterly`` → 1st of Jan/Apr/Jul/Oct 09:00

Each task delegates to ``ComplianceMonitorService.run_frequency_batch`` and
returns a small dict for Celery result inspection.
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session
from backend.app.motors.m_compliance_monitor.service import (
    ComplianceMonitorService,
)


shared_task = celery_app.task


async def _run_batch(frequency: str) -> dict[str, Any]:
    async with async_session() as session:
        try:
            svc = ComplianceMonitorService(session)
            await svc.sync_registry()
            outcomes = await svc.run_frequency_batch(frequency)
            ran = len(outcomes)
            alerts_created = sum(1 for o in outcomes if o.alert_created)
            auto_resolved = sum(
                1 for o in outcomes if o.auto_resolved_alert_id is not None
            )
            # #J-GAP2 · R6 dogfooding: trazar el batch de checks en audit_log
            # (antes los beats Celery NO se auto-trazaban). Reusa el helper
            # canónico _emit_monitor_audit (system-level · project/client NULL).
            import uuid as _uuid

            from backend.app.motors.m_compliance_monitor.api import (
                _emit_monitor_audit,
            )
            await _emit_monitor_audit(
                session,
                tabla="compliance_checks",
                registro_id=_uuid.uuid4(),
                accion="compliance.batch.run",
                usuario="system",
                payload={
                    "frequency": frequency,
                    "ran": ran,
                    "alerts_created": alerts_created,
                    "auto_resolved": auto_resolved,
                },
            )
            await session.commit()
            return {
                "frequency": frequency,
                "ran": ran,
                "alerts_created": alerts_created,
                "auto_resolved": auto_resolved,
            }
        except Exception:
            await session.rollback()
            raise


async def _generate_weekly_report() -> dict[str, Any]:
    async with async_session() as session:
        try:
            svc = ComplianceMonitorService(session)
            result = await svc.generate_weekly_report()
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


@shared_task(name="compliance.run_daily")
def run_daily_checks() -> dict[str, Any]:
    """Run all ``daily`` cadence checks."""
    logger.info("[compliance] daily batch starting")
    return asyncio.run(_run_batch("daily"))


@shared_task(name="compliance.run_weekly")
def run_weekly_checks() -> dict[str, Any]:
    """Run weekly checks + generate weekly status report."""
    logger.info("[compliance] weekly batch starting")
    batch = asyncio.run(_run_batch("weekly"))
    report = asyncio.run(_generate_weekly_report())
    return {"batch": batch, "report": report}


@shared_task(name="compliance.run_monthly")
def run_monthly_checks() -> dict[str, Any]:
    """Run monthly cadence checks."""
    logger.info("[compliance] monthly batch starting")
    return asyncio.run(_run_batch("monthly"))


@shared_task(name="compliance.run_quarterly")
def run_quarterly_checks() -> dict[str, Any]:
    """Run quarterly cadence checks."""
    logger.info("[compliance] quarterly batch starting")
    return asyncio.run(_run_batch("quarterly"))
