"""Celery task · alerta auditoría bienal art.31 RD 311/2022 (MB-13.4 · ADR-035).

Daily 08:00 · genera alertas ``bienal_art31`` per AuditScheduleEntry con
``next_audit_due`` ≤ 90 días. Severity ``critical`` si <30 días, sino
``warning``.

Dedup: skip si ya existe alert no-acknowledged para misma audit_schedule_id
(via ``metadata_jsonb->>'audit_schedule_id'`` lookup).

Future: tracking ``notification_sent_at`` per audit_schedule fila +
columna `last_alert_severity` (TODO post-MB-13.4 · MB-18 quizás).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import text as sa_text

from backend.app.core.celery_app import celery_app
from backend.app.database import async_session
from backend.app.motors.m18_communication.alert_service import AlertService

logger = logging.getLogger(__name__)


@celery_app.task(name="m27_conformity.check_biannual_audits_due")
def check_biannual_audits_due() -> int:
    """Trigger alertas auditoría bienal próxima (90d window)."""
    import asyncio

    return asyncio.run(_check_biannual_audits_due())


async def _check_biannual_audits_due() -> int:
    """Implementación async · retorna count alertas creadas."""
    async with async_session() as db:
        cutoff = date.today() + timedelta(days=90)

        rows = await db.execute(
            sa_text(
                "SELECT a.id::text, a.project_id::text, a.audit_type, "
                "       a.next_audit_due "
                "FROM audit_schedules a "
                "WHERE a.deleted_at IS NULL "
                "  AND a.next_audit_due <= :cutoff "
                "  AND NOT EXISTS ("
                "    SELECT 1 FROM alert_queue q "
                "    WHERE q.category = 'bienal_art31' "
                "      AND q.acknowledged_at IS NULL "
                "      AND q.metadata_jsonb->>'audit_schedule_id' = a.id::text "
                "  )"
            ),
            {"cutoff": cutoff},
        )
        upcoming = rows.fetchall()

        if not upcoming:
            return 0

        service = AlertService(db)
        today = date.today()
        created = 0

        for row in upcoming:
            audit_id, project_id, audit_type, due_date = row
            days_remaining = (due_date - today).days
            severity = "critical" if days_remaining < 30 else "warning"

            try:
                await service.trigger_alert(
                    project_id=project_id,
                    severity=severity,
                    category="bienal_art31",
                    title=(
                        f"Auditoría bienal próxima ({days_remaining} días)"
                    ),
                    description=(
                        f"Art. 31 RD 311/2022 · auditoría {audit_type} "
                        f"obligatoria · vence {due_date}"
                    ),
                    action_url=f"/admin/projects/{project_id}/conformity",
                    triggered_by="check_biannual_audits_due",
                    metadata={
                        "audit_schedule_id": audit_id,
                        "days_remaining": days_remaining,
                        "audit_type": audit_type,
                    },
                )
                created += 1
            except Exception:  # pragma: no cover · best-effort
                logger.exception(
                    "Failed creating bienal alert for project %s",
                    project_id,
                )

        await db.commit()
        logger.info("check_biannual_audits_due · %d alerts created", created)
        return created
