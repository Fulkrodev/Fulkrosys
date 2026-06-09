"""Celery task wrapper · coach proactivo nudge dispatch.

Sesión 3B-2B.8 CLUSTER 2 Phase 2C · Pattern #15 cumulative.

Stub-friendly: si Celery no instalado (dev/tests), `@celery_app.task`
actúa como identity decorator. Tasks invocable direct via
``scan_pending_nudges_async()`` desde tests.
"""
from __future__ import annotations

import asyncio
import logging

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session


logger = logging.getLogger(__name__)


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Reutiliza event loop o crea uno nuevo · safe en Celery sync worker."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@celery_app.task(name="m11_copiloto.scan_pending_nudges")
def scan_pending_nudges_task() -> dict:
    """Daily scheduled · compute pending nudges + dispatch best-effort.

    Beat schedule: daily 09:15 ES (15 min after notifications.scan_client_inactivity).

    Returns:
        dict con stats: {dispatched, failed, total}.
    """
    logger.info("m11_copiloto.scan_pending_nudges task triggered")
    loop = _ensure_loop()
    return loop.run_until_complete(scan_pending_nudges_async())


async def scan_pending_nudges_async() -> dict:
    """Async core · compute_pending_nudges + dispatch_nudges within session."""
    from backend.app.motors.m11_copiloto.nudge_scheduler import (
        compute_pending_nudges,
        dispatch_nudges,
    )

    async with async_session() as db:
        try:
            nudges = await compute_pending_nudges(db)
            if not nudges:
                logger.info("coach.scan_pending_nudges · no nudges pending")
                return {"dispatched": 0, "failed": 0, "total": 0}
            result = await dispatch_nudges(db, nudges)
            logger.info(
                "coach.scan_pending_nudges · dispatched=%d failed=%d total=%d",
                result["dispatched"], result["failed"], result["total"],
            )
            return result
        except Exception:
            logger.exception(
                "coach.scan_pending_nudges · scan failed · transaction rollback",
            )
            await db.rollback()
            raise


@celery_app.task(name="m11_copiloto.scan_pending_admin_nudges")
def scan_pending_admin_nudges_task() -> dict:
    """Daily scheduled · push proactivo ADMIN in-app (#22 Ola 5).

    Avisa a Marcos de proyectos con acción urgent que lleva >72h sin abrir
    (cooldown 7d · solo urgent). NO email.
    """
    logger.info("m11_copiloto.scan_pending_admin_nudges task triggered")
    loop = _ensure_loop()
    return loop.run_until_complete(scan_pending_admin_nudges_async())


async def scan_pending_admin_nudges_async() -> dict:
    """Async core · compute + dispatch admin nudges within session."""
    from backend.app.motors.m11_copiloto.admin_nudge_scheduler import (
        compute_pending_admin_nudges,
        dispatch_admin_nudges,
    )

    async with async_session() as db:
        try:
            nudges = await compute_pending_admin_nudges(db)
            if not nudges:
                logger.info("admin_nudge.scan · no nudges pending")
                return {"dispatched": 0, "failed": 0, "total": 0}
            result = await dispatch_admin_nudges(db, nudges)
            logger.info(
                "admin_nudge.scan · dispatched=%d failed=%d total=%d",
                result["dispatched"], result["failed"], result["total"],
            )
            return result
        except Exception:
            logger.exception(
                "admin_nudge.scan · scan failed · transaction rollback",
            )
            await db.rollback()
            raise
