"""Celery tasks · m_observability · sub-atom 1.E.1.B.3.E.

Background eval run wrapper · invocable desde Celery beat (post-B.3.E
scheduled patterns) OR ad-hoc desde admin endpoints.

Skeleton phase (B.3.D Path C-light): tasks NO ejecutan LLM calls (entries
skipped si capability pending) · seguro para background processing.
"""
from __future__ import annotations

import asyncio
import uuid

from loguru import logger

try:
    from backend.app.core.celery_app import celery_app  # type: ignore[import-not-found]
    _CELERY_AVAILABLE = True
except Exception:  # noqa: BLE001
    _CELERY_AVAILABLE = False
    celery_app = None  # type: ignore[assignment]


async def _run_eval_async(run_id_str: str, agent_name: str, version: str) -> None:
    from backend.app.database import async_session
    from backend.app.motors.m_observability.golden_eval_runs_service import (
        execute_eval_run_sync,
    )

    async with async_session() as db:
        await execute_eval_run_sync(
            db,
            run_id=uuid.UUID(run_id_str),
            agent_name=agent_name,
            version=version,
        )


if _CELERY_AVAILABLE:

    @celery_app.task(name="m_observability.run_golden_eval_async", bind=True)
    def run_golden_eval_async(
        self,  # noqa: ANN001
        run_id_str: str,
        agent_name: str,
        version: str = "v1",
    ) -> dict:
        """Celery task · async wrapper para execute_eval_run_sync."""
        try:
            asyncio.run(_run_eval_async(run_id_str, agent_name, version))
            return {"status": "completed", "run_id": run_id_str}
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "golden_eval task failed run_id=%s · %s", run_id_str, exc,
            )
            return {"status": "failed", "run_id": run_id_str, "error": str(exc)}
