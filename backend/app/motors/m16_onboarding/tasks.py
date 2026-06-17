"""Motor 16 — Celery tasks programadas (onboarding / OAuth).

I8 (campaña auditoría 2026-06-17): el servicio ``oauth_state_service.cleanup_expired``
existía pero NUNCA se ejecutaba (no estaba en el beat) → los OAuth state tokens
expirados/consumidos se acumulaban indefinidamente. Esta task lo programa
(diario 04:15 ES) siguiendo el patrón async-session de m29/m23/m26.
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from backend.app.core.celery_app import celery_app


@celery_app.task(name="m16.cleanup_expired_oauth_states")
def cleanup_expired_oauth_states() -> dict[str, Any]:
    """Purga OAuth state tokens expirados/consumidos (>1h). Scheduled diario.

    Reusa ``oauth_state_service.cleanup_expired`` (lógica ya existente).
    """
    return asyncio.run(_cleanup_expired_oauth_states_async())


async def _cleanup_expired_oauth_states_async() -> dict[str, Any]:
    from sqlalchemy import text

    from backend.app.database import async_session
    from backend.app.motors.m16_onboarding.oauth_state_service import (
        cleanup_expired,
    )

    async with async_session() as db:
        # Admin task fuera del request cliente → bypass RLS controlado.
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        deleted = await cleanup_expired(db)
        await db.commit()

    logger.info("m16 cleanup_expired_oauth_states: deleted={}", deleted)
    return {"task": "m16.cleanup_expired_oauth_states", "deleted": deleted}
