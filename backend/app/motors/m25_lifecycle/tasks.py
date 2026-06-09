"""M25 Paso 4 — Celery tasks for grace period + backup expiration.

Dos tareas programadas diarias:

1. ``lifecycle_grace_period_check`` (04:30 Europe/Madrid)
   Revisa todos los proyectos en ENDED_CHURN con grace fields y dispara
   los hitos calendaricos (dia 150, 180, 210, 240).

2. ``lifecycle_backup_expiration_check`` (05:00 Europe/Madrid)
   Elimina de MinIO los archived_backups cuyo expires_at <= now.

En dev/tests (sin Celery), estas tasks son invocables directamente
como funciones sync a traves de los helpers async del service.
"""
from __future__ import annotations

import asyncio
import logging
import os

from backend.app.core.celery_app import celery_app


logger = logging.getLogger(__name__)


def _run_async(coro):
    """Ejecuta una coroutine en un event loop dedicado."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # En un worker de Celery, crear un loop nuevo (evita colisiones)
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        return loop.run_until_complete(coro)
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()


async def _run_grace_check():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from backend.app.config import get_settings
    from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
        process_grace_period_checkpoints,
    )

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                result = await process_grace_period_checkpoints(
                    session,
                    base_url=os.environ.get(
                        "FULKRO_PORTAL_BASE_URL",
                        "https://portal.fulkro.es",
                    ),
                    marcos_email=os.environ.get(
                        "FULKRO_MARCOS_EMAIL",
                        "marcosmata@fulkro.es",
                    ),
                )
                await trans.commit()
                return result
            except Exception:  # pragma: no cover
                await trans.rollback()
                raise
            finally:
                await session.close()
    finally:
        await engine.dispose()


async def _run_backup_expiration():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from backend.app.config import get_settings
    from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
        process_backup_expirations,
    )

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                result = await process_backup_expirations(session)
                await trans.commit()
                return result
            except Exception:  # pragma: no cover
                await trans.rollback()
                raise
            finally:
                await session.close()
    finally:
        await engine.dispose()


@celery_app.task(name="m25.lifecycle_grace_period_check")
def lifecycle_grace_period_check() -> dict:
    """Celery task — diaria. Procesa hitos de grace period."""
    logger.info("M25 lifecycle_grace_period_check: arranque")
    result = _run_async(_run_grace_check())
    logger.info("M25 lifecycle_grace_period_check: resultado=%s", result)
    return result


@celery_app.task(name="m25.lifecycle_backup_expiration_check")
def lifecycle_backup_expiration_check() -> dict:
    """Celery task — diaria. Borra backups expirados de MinIO."""
    logger.info("M25 lifecycle_backup_expiration_check: arranque")
    result = _run_async(_run_backup_expiration())
    logger.info(
        "M25 lifecycle_backup_expiration_check: resultado=%s", result,
    )
    return result
