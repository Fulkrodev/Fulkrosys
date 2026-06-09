"""Golden eval runs service · sub-atom 1.E.1.B.3.E.

Admin trigger + history tracking para `/admin/llm-observability/golden-eval/`.

Helpers:
  - list_available_datasets · descubre folder agent_name/v<version>.json
  - trigger_eval_run · INSERT golden_eval_runs row status=queued
  - persist_eval_completion · update post run_eval ejecutado
  - list_runs · query history per agent + days
  - get_run · drill-down detail

Platform-global · admin-only · NO RLS.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_observability.eval_runner import (
    DatasetEvalReport,
    run_eval,
)
from backend.app.motors.m_observability.golden_datasets_loader import (
    list_available_datasets as _list_available_datasets,
)
from backend.app.motors.m_observability.models import (
    GoldenEvalRun,
    GoldenEvalRunStatus,
)


def list_available_datasets() -> list[dict[str, str]]:
    """Returns datasets disponibles para trigger via admin UI."""
    pairs = _list_available_datasets()
    return [
        {"agent_name": agent, "version": version}
        for agent, version in pairs
    ]


async def trigger_eval_run(
    db: AsyncSession,
    *,
    agent_name: str,
    version: str = "v1",
    triggered_by_user_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> GoldenEvalRun:
    """INSERT golden_eval_runs row status=queued · returns persisted entity."""
    run = GoldenEvalRun(
        agent_name=agent_name,
        dataset_version=version,
        triggered_by_user_id=triggered_by_user_id,
        status=GoldenEvalRunStatus.QUEUED.value,
        metadata_=metadata,
    )
    db.add(run)
    await db.flush()
    await db.commit()
    return run


async def persist_eval_completion(
    db: AsyncSession,
    *,
    run_id: uuid.UUID,
    report: DatasetEvalReport,
) -> GoldenEvalRun | None:
    """UPDATE run row con report results post eval execution."""
    stmt = select(GoldenEvalRun).where(GoldenEvalRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        return None

    failed_entry_ids = [
        r.entry_id for r in report.entry_results
        if not r.passed and not r.skipped
    ]
    run.status = GoldenEvalRunStatus.COMPLETED.value
    run.completed_at = datetime.now(timezone.utc)
    run.regression_score = report.pass_rate
    run.severity = report.severity
    run.entries_in_dataset = report.entries_in_dataset
    run.entries_evaluated = report.total_entries
    run.entries_passed = report.passed
    run.entries_failed = report.failed
    run.failed_entry_ids = failed_entry_ids
    await db.flush()
    await db.commit()
    return run


async def persist_eval_failure(
    db: AsyncSession,
    *,
    run_id: uuid.UUID,
    error_message: str,
) -> GoldenEvalRun | None:
    """UPDATE run row status=failed con error_message."""
    stmt = select(GoldenEvalRun).where(GoldenEvalRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        return None
    run.status = GoldenEvalRunStatus.FAILED.value
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = error_message[:2000]
    await db.flush()
    await db.commit()
    return run


async def list_runs(
    db: AsyncSession,
    *,
    agent_name: str | None = None,
    days: int = 30,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query historical runs · optional filter per agent · last N days."""
    days = max(1, min(int(days), 365))
    limit = max(1, min(int(limit), 200))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(GoldenEvalRun)
        .where(GoldenEvalRun.triggered_at > cutoff)
        .order_by(desc(GoldenEvalRun.triggered_at))
        .limit(limit)
    )
    if agent_name is not None:
        stmt = stmt.where(GoldenEvalRun.agent_name == agent_name)

    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_run(r) for r in rows]


async def get_run(
    db: AsyncSession,
    *,
    run_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Drill-down run detail."""
    stmt = select(GoldenEvalRun).where(GoldenEvalRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        return None
    return _serialize_run(run)


def _serialize_run(run: GoldenEvalRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "agent_name": run.agent_name,
        "dataset_version": run.dataset_version,
        "triggered_by_user_id": (
            str(run.triggered_by_user_id) if run.triggered_by_user_id else None
        ),
        "triggered_at": run.triggered_at.isoformat(),
        "completed_at": (
            run.completed_at.isoformat() if run.completed_at else None
        ),
        "status": run.status,
        "regression_score": run.regression_score,
        "severity": run.severity,
        "entries_in_dataset": run.entries_in_dataset,
        "entries_evaluated": run.entries_evaluated,
        "entries_passed": run.entries_passed,
        "entries_failed": run.entries_failed,
        "failed_entry_ids": run.failed_entry_ids,
        "error_message": run.error_message,
        "metadata": run.metadata_,
    }


async def execute_eval_run_sync(
    db: AsyncSession,
    *,
    run_id: uuid.UUID,
    agent_name: str,
    version: str = "v1",
) -> GoldenEvalRun | None:
    """Execute eval synchronously (NO Celery dependency) y persist results.

    Service-layer helper · llamado desde endpoint POST trigger OR Celery
    task wrapper. Status: queued → running → completed/failed transition
    handled aquí · NO LLM call si capability pending (entries skipped).
    """
    # Mark running
    stmt = select(GoldenEvalRun).where(GoldenEvalRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        return None
    run.status = GoldenEvalRunStatus.RUNNING.value
    await db.flush()
    await db.commit()

    try:
        # Import side-effect register evaluators
        from backend.app.motors.m_observability import (
            evaluators,  # noqa: F401
        )
        report = run_eval(agent_name, version)
        return await persist_eval_completion(
            db, run_id=run_id, report=report,
        )
    except Exception as exc:  # noqa: BLE001
        return await persist_eval_failure(
            db, run_id=run_id, error_message=str(exc),
        )
