"""M28 Change Governance — tasks Celery programadas.

D5 (campaña fix auditoría 2026-06-17): refresca la vista materializada
``mv_drift_summary_10x4`` que alimenta GET /api/v1/projects/{id}/drift-summary.
Antes NINGÚN job la refrescaba en producción (el endpoint devolvía datos
obsoletos/vacíos · role_topology_extensions_api documentaba "refresh via job M28
jobs.py" que no existía).

Usa la función ``fn_refresh_drift_summary()`` SECURITY DEFINER (migración
``m28_refresh_drift_summary_fn_001``) porque el worker corre como ``fulkro_app``
(NOSUPERUSER, no-owner) y no puede REFRESH la matview (OWNER fulkro) directamente.
"""
from __future__ import annotations

from loguru import logger

from backend.app.core.celery_app import celery_app


@celery_app.task(name="m28.refresh_drift_summary")
def refresh_drift_summary() -> dict:
    """Refresca mv_drift_summary_10x4 vía fn_refresh_drift_summary() SECURITY DEFINER.

    Scheduled: lunes 06:45 (tras m23.drift_weekly_compute 06:00 que escribe los
    retainer_drift_events que la matview agrega).
    """
    import asyncio

    from sqlalchemy import text

    from backend.app.database import async_session

    async def _run() -> dict:
        async with async_session() as session:
            await session.execute(text("SELECT fn_refresh_drift_summary()"))
            await session.commit()
        return {"status": "refreshed", "view": "mv_drift_summary_10x4"}

    try:
        result = asyncio.run(_run())
        logger.info("m28.refresh_drift_summary OK")
        return result
    except Exception as exc:  # pragma: no cover
        logger.exception("m28.refresh_drift_summary failed")
        return {"status": "failed", "error": str(exc)[:300]}
