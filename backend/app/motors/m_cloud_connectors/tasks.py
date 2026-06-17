"""Celery tasks · cloud-connectors retainer monitoring (sub-atom 1.D.X.L v3.12).

Beat schedule registrado en backend.app.core.celery_app:
  - cloud-retainer-daily-diagnosis  · daily 04:00 Europe/Madrid
    Per project con CloudConnector activo · re-ejecuta DiagnosticGapEngine.
    Detecta nuevos gaps + auto-resuelve los que dejan de emitir.

  - cloud-retainer-monthly-digest   · día 1 mes 09:00 Europe/Madrid
    Per project en fase RETAINER · genera digest mensual compliance summary.
    Stub para M06 template generation (T1 polish post-piloto).

Compatibility:
  - Si celery no está instalado · tasks son funciones plain (stub @task decorador
    es identity per celery_app stub fallback).
  - Tasks SIN cloud connectors activos · NO hacen nada (sync zero · NO ruido).
  - Tasks idempotentes · 2 ejecuciones consecutivas idem state.

R1 sostener · gap engine pipeline 100% determinístico · LLM NO invocado.
ADR-014 read-only sostener · NO modifica nada en cloud cliente.
OPS-045 sostener · reuse DiagnosticGapEngine + CloudConnectorService existing.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session, set_tenant_context
from backend.app.motors.m_cloud_connectors.diagnostic_gap_engine import (
    DiagnosticGapEngine,
)
from backend.app.motors.m_cloud_connectors.digest_service import (
    generate_monthly_digest_for_project,
)
from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorStatus,
    CloudGap,
)


logger = logging.getLogger(__name__)


# ==================================================================
# Helpers (puros · sin celery · testeables directamente)
# ==================================================================


async def list_projects_with_active_connectors(
    db: AsyncSession,
) -> list[uuid.UUID]:
    """Project ids con al menos 1 CloudConnector activo (no revoked).

    Descubrimiento CROSS-TENANT: el task corre con async_session (rol fulkro_app,
    NO fulkro_migrate como decía el docstring antiguo), así que la RLS de
    cloud_connectors (por app.current_project_id) ocultaría TODO sin contexto →
    el beat escaneaba 0 proyectos. Elevamos a bypassrls SOLO para el inventario;
    el bucle posterior fija set_tenant_context por proyecto (correcto).
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(CloudConnector.project_id)
            .where(
                CloudConnector.revoked_at.is_(None),
                CloudConnector.status.in_([
                    CloudConnectorStatus.CONNECTED.value,
                    CloudConnectorStatus.SYNCING.value,
                    CloudConnectorStatus.SYNC_ERROR.value,
                    CloudConnectorStatus.PENDING_OAUTH.value,
                ]),
            )
            .distinct()
        )
        return [row[0] for row in res.all()]
    finally:
        await db.execute(text("RESET ROLE"))


async def run_diagnosis_for_project_id(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Set tenant context + run gap engine · devuelve dict summary."""
    await set_tenant_context(db, project_id=project_id)
    engine = DiagnosticGapEngine(db)
    report = await engine.run_diagnosis(project_id=project_id)
    return {
        "project_id": str(project_id),
        "category": report.category,
        "rules_evaluated": report.rules_evaluated,
        "findings_emitted": report.findings_emitted,
        "gaps_created": report.gaps_created,
        "gaps_updated": report.gaps_updated,
        "gaps_resolved": report.gaps_resolved,
        "no_cloud_data": report.no_cloud_data,
    }


async def compute_compliance_snapshot(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Snapshot compliance · counts gaps abiertos por severity.

    Compute simple para digest mensual · 0 LLM · puro SQL aggregate.
    """
    await set_tenant_context(db, project_id=project_id)
    res = await db.execute(
        select(CloudGap.severity, text("COUNT(*) AS cnt"))
        .where(
            CloudGap.project_id == project_id,
            CloudGap.resolved_at.is_(None),
        )
        .group_by(CloudGap.severity)
    )
    counts_by_severity = {row[0]: row[1] for row in res.all()}
    total_open = sum(counts_by_severity.values())
    # Compliance score simple: 100 - critical*10 - high*5 - medium*2 - low*1
    score = max(0, 100
        - counts_by_severity.get("critical", 0) * 10
        - counts_by_severity.get("high", 0) * 5
        - counts_by_severity.get("medium", 0) * 2
        - counts_by_severity.get("low", 0) * 1,
    )
    return {
        "project_id": str(project_id),
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "open_gaps_total": total_open,
        "open_gaps_by_severity": counts_by_severity,
        "compliance_score": score,
    }


async def list_retainer_active_project_ids(db: AsyncSession) -> list[uuid.UUID]:
    """Project ids en fase RETAINER (post-certification monitoring).

    M5: ``projects`` es FORCE RLS por ``app.current_project_id``; el task corre
    con async_session (rol fulkro_app, SIN contexto de proyecto) → sin elevar, el
    SELECT devuelve 0 filas y el digest mensual NUNCA se generaba. Elevamos a
    bypassrls SOLO para el inventario cross-tenant; el bucle posterior fija
    ``set_tenant_context`` por proyecto (mismo patrón que
    ``list_projects_with_active_connectors``).
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(text(
            "SELECT id FROM projects "
            "WHERE lifecycle_state = 'RETAINER' "
            "AND deleted_at IS NULL"
        ))
        return [uuid.UUID(str(row[0])) for row in res.all()]
    finally:
        await db.execute(text("RESET ROLE"))


# ==================================================================
# Celery tasks
# ==================================================================


@celery_app.task(name="cloud_connectors.daily_diagnosis", bind=True)
def cloud_retainer_daily_diagnosis_task(self) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Daily 04:00 ES · re-ejecuta DiagnosticGapEngine per project con cloud.

    Devuelve summary {projects_scanned, total_gaps_created, ...} para
    inspección via celery results backend.
    """
    return asyncio.run(_async_daily_diagnosis())


@celery_app.task(name="cloud_connectors.monthly_digest", bind=True)
def cloud_retainer_monthly_digest_task(self) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Día 1 mes 09:00 ES · genera digest mensual per project en RETAINER.

    En L-light produce SOLO los snapshots compliance · auto-send via M18
    se completa en T1 polish post-piloto.
    """
    return asyncio.run(_async_monthly_digest())


# ==================================================================
# Async impls (separadas del decorator celery · testeables direct)
# ==================================================================


async def _async_daily_diagnosis() -> dict[str, Any]:
    """Recorre projects activos y ejecuta gap engine · acumula summary."""
    async with async_session() as db:
        try:
            project_ids = await list_projects_with_active_connectors(db)
        except Exception as exc:  # noqa: BLE001
            logger.exception("daily_diagnosis · failed to list projects · %s", exc)
            return {"projects_scanned": 0, "error": str(exc)}

        summaries: list[dict[str, Any]] = []
        for pid in project_ids:
            try:
                summary = await run_diagnosis_for_project_id(db, pid)
                summaries.append(summary)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "daily_diagnosis · project %s failed · %s", pid, exc,
                )
                summaries.append({
                    "project_id": str(pid),
                    "error": str(exc),
                })
        await db.commit()

    return {
        "projects_scanned": len(project_ids),
        "total_findings": sum(
            s.get("findings_emitted", 0) for s in summaries
        ),
        "total_gaps_created": sum(
            s.get("gaps_created", 0) for s in summaries
        ),
        "total_gaps_resolved": sum(
            s.get("gaps_resolved", 0) for s in summaries
        ),
        "projects_summaries": summaries,
    }


async def _async_monthly_digest() -> dict[str, Any]:
    """Recorre projects RETAINER · invoca digest_service per project.

    Delega a `generate_monthly_digest_for_project` (service compartido con
    admin manual trigger) · persiste CloudDigestSnapshot + audit_log entry.
    """
    async with async_session() as db:
        try:
            project_ids = await list_retainer_active_project_ids(db)
        except Exception as exc:  # noqa: BLE001
            logger.exception("monthly_digest · failed to list projects · %s", exc)
            return {"projects_processed": 0, "error": str(exc)}

        snapshots: list[dict[str, Any]] = []
        for pid in project_ids:
            try:
                await set_tenant_context(db, project_id=pid)
                snapshot = await generate_monthly_digest_for_project(
                    db, project_id=pid, triggered_by="celery_monthly",
                )
                snapshots.append({
                    "project_id": str(pid),
                    "snapshot_id": str(snapshot.id),
                    "compliance_score": snapshot.compliance_score,
                    "open_gaps_total": snapshot.open_gaps_total,
                })
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "monthly_digest · project %s failed · %s", pid, exc,
                )
        await db.commit()

    return {
        "projects_processed": len(snapshots),
        "snapshots": snapshots,
    }
