"""Celery task · DPC anual anniversary check · SAN-E v3.MB-6 atom 2.

Daily 08:30 Europe/Madrid · escanea conformidad inicial firmadas:
  - Compute anniversary_date = conformidad_signed_at + 12m * year_offset
  - Si anniversary_date <= today + 30 días Y NO existe DPC draft para year:
    * Crea DPC anual draft (idempotent via UNIQUE constraint)
    * AlertService trigger alert category 'dpc_due' (severity warning <30d / critical <7d)
  - Dedup: skip si alert no-acknowledged existe para misma (project_id, anniversary_year)

Pattern replicado de m27_conformity/biannual_alert_task.py (art.31).

ADR-035 v2 · art.25 RD 311/2022 · CCN-STIC 806 anniversary-based.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import text as sa_text

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session
from backend.app.motors.m18_communication.alert_service import AlertService
from backend.app.motors.m27_conformity.dpc_anual_service import (
    ALERT_LEAD_DAYS,
    CRITICAL_LEAD_DAYS,
    DpcAnualService,
)


logger = logging.getLogger(__name__)


@celery_app.task(name="m27_conformity.check_dpc_anual_anniversaries")
def check_dpc_anual_anniversaries() -> int:
    """Trigger DPC anual drafts + alerts · 30d antes anniversary."""
    return asyncio.run(_check_dpc_anual_anniversaries())


async def _check_dpc_anual_anniversaries() -> int:
    """Implementación async · retorna count alertas creadas."""
    today = date.today()
    cutoff = today + timedelta(days=ALERT_LEAD_DAYS)
    alerts_created = 0

    async with async_session() as db:
        # Query conformidad inicial firmadas (base date anniversary)
        rows = await db.execute(
            sa_text(
                "SELECT project_id::text, signed_at "
                "FROM basic_declarations "
                "WHERE declaration_type IN ('initial', 'commitment_pre_certification') "
                "AND signed_at IS NOT NULL"
            )
        )
        candidates = list(rows)

        svc = DpcAnualService(db)
        alert_svc = AlertService(db)

        for project_id_str, signed_at in candidates:
            try:
                import uuid as _uuid
                project_id = _uuid.UUID(project_id_str)
            except Exception:
                logger.warning(
                    "DPC anual: project_id inválido %s · skip", project_id_str,
                )
                continue

            # Calcular próximo anniversary year futuro (1, 2, 3...) que ≤ cutoff
            base_date = signed_at.date()
            year_offset = 1
            while True:
                anniversary_date = base_date.replace(
                    year=base_date.year + year_offset,
                )
                if anniversary_date > cutoff:
                    break
                anniversary_year = anniversary_date.year
                days_to_anniversary = (anniversary_date - today).days

                # Dedup: NO crear alert si una no-acknowledged existe para misma year
                dup_check = await db.execute(
                    sa_text(
                        "SELECT 1 FROM alert_queue "
                        "WHERE project_id = :pid "
                        "AND category = 'dpc_due' "
                        "AND acknowledged_at IS NULL "
                        "AND metadata_jsonb->>'anniversary_year' = :year"
                    ),
                    {"pid": project_id_str, "year": str(anniversary_year)},
                )
                if dup_check.first() is not None:
                    year_offset += 1
                    continue

                # Create DPC draft (idempotent via UNIQUE partial)
                try:
                    decl = await svc.create_dpc_anual_draft(
                        project_id=project_id,
                        anniversary_year=anniversary_year,
                    )
                except Exception as exc:
                    logger.error(
                        "DPC anual draft falló project=%s year=%s · %s",
                        project_id_str, anniversary_year, exc,
                    )
                    year_offset += 1
                    continue

                # Trigger alert
                severity = (
                    "critical"
                    if days_to_anniversary <= CRITICAL_LEAD_DAYS
                    else "warning"
                )
                try:
                    await alert_svc.trigger_alert(
                        project_id=project_id,
                        severity=severity,
                        category="dpc_due",
                        title=(
                            f"DPC anual {anniversary_year} próxima "
                            f"· {days_to_anniversary} días"
                        ),
                        description=(
                            f"Anniversary fecha {anniversary_date.isoformat()} "
                            f"· revisa y firma en /client-portal/dpc-anual"
                        ),
                        action_url="/client-portal/dpc-anual",
                        triggered_by="m27_conformity.check_dpc_anual_anniversaries",
                        metadata={
                            "anniversary_year": str(anniversary_year),
                            "anniversary_date": anniversary_date.isoformat(),
                            "declaration_id": str(decl.id),
                            "days_to_anniversary": days_to_anniversary,
                        },
                    )
                    alerts_created += 1
                except Exception as exc:
                    logger.error(
                        "AlertService trigger falló · %s", exc,
                    )

                year_offset += 1

        await db.commit()

    logger.info("DPC anual check completed · %d alerts created", alerts_created)
    return alerts_created
