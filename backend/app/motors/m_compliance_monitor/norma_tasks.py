"""Celery tasks for per-norma compliance reports (mini-atom 3).

Master task ``compliance.generate_norma_report(norma_key)`` runs one
specific norma. ``compliance.generate_all_norma_reports`` is a fallback
scheduled monthly that iterates every registered plugin.
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session
from backend.app.motors.m_compliance_monitor.norma_reports_service import (
    ComplianceNormaReportsService,
    NormaNotRegisteredError,
)
from backend.app.motors.m_compliance_monitor.normas import NormaRegistry


shared_task = celery_app.shared_task


async def _generate_one(norma_key: str) -> dict[str, Any]:
    async with async_session() as session:
        try:
            svc = ComplianceNormaReportsService(session)
            row = await svc.generate_report(norma_key)
            await session.commit()
            return {
                "norma_key": norma_key,
                "report_id": str(row.id),
                "score": float(row.compliance_score),
                "status": row.status,
            }
        except NormaNotRegisteredError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise


async def _generate_all() -> dict[str, Any]:
    async with async_session() as session:
        try:
            svc = ComplianceNormaReportsService(session)
            results = await svc.generate_all_due()
            await session.commit()
            return {
                "count": len(results),
                "norma_keys": [r.norma_key for r in results],
            }
        except Exception:
            await session.rollback()
            raise


@shared_task(name="compliance.generate_norma_report")
def generate_norma_report(norma_key: str) -> dict[str, Any]:
    logger.info("[compliance] generating norma report for {}", norma_key)
    return asyncio.run(_generate_one(norma_key))


@shared_task(name="compliance.generate_all_norma_reports")
def generate_all_norma_reports() -> dict[str, Any]:
    logger.info("[compliance] generating reports for every registered norma")
    return asyncio.run(_generate_all())


def build_beat_entries() -> dict[str, dict[str, Any]]:
    """Return Celery beat entries (dict form) for every registered norma.

    Called by ``core/celery_app.py`` after the static beat schedule is
    constructed. The crontab is built from the JSON-safe descriptor each
    plugin returns via ``get_scheduler_config()``.
    """
    try:
        from celery.schedules import crontab
    except ImportError:  # pragma: no cover — dev/test without Celery
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for module in NormaRegistry.get_all():
        cfg = module.get_scheduler_config()
        key = f"compliance-norma-report-{module.norma_key.lower()}"
        entries[key] = {
            "task": cfg["task"],
            "schedule": crontab(**cfg["cron"]),
            "args": cfg["args"],
        }
    return entries
