"""AlertService · trigger + list + acknowledge alertas (MB-13.4 · ADR-035).

Triggers SSE ``alert_new`` event al insertar para refresh UI sin polling.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.models.alerts import Alert

logger = logging.getLogger(__name__)


_VALID_SEVERITIES = {"info", "warning", "critical"}
_VALID_CATEGORIES = {
    "bienal_art31",
    "payment_overdue_aapp",
    "client_inactivity",
    "evidence_stale",
    "retainer_overdue",
    "milestone_due",
    "workflow_blocked",
    "audit_due",
    "rgpd_72h",
    "contract_milestone",
    "renewal_due",
    "other",
}


class AlertService:
    """Gestión alert_queue · trigger + list + acknowledge."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_alert(
        self,
        project_id: UUID,
        severity: str,
        category: str,
        title: str,
        description: str = "",
        action_url: str = "",
        triggered_by: str = "system",
        metadata: Optional[dict] = None,
    ) -> Alert:
        """Crea alert + dispatch SSE ``alert_new`` event."""
        if severity not in _VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity: {severity!r}. Allowed: {_VALID_SEVERITIES}",
            )
        if category not in _VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category!r}. Allowed: {_VALID_CATEGORIES}",
            )

        alert = Alert(
            project_id=project_id,
            severity=severity,
            category=category,
            title=title,
            description=description or None,
            action_url=action_url or None,
            triggered_by=triggered_by,
            metadata_jsonb=metadata or {},
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)

        try:
            await sse_dispatcher.dispatch(
                channel=f"project:{project_id}",
                event_type="alert_new",
                data={
                    "alert_id": str(alert.id),
                    "severity": severity,
                    "category": category,
                    "title": title,
                },
            )
        except Exception:  # pragma: no cover · best-effort SSE
            logger.warning("SSE dispatch failed for alert_new", exc_info=True)

        return alert

    async def list_active_alerts(
        self, project_id: UUID,
    ) -> list[Alert]:
        """Alertas no acknowledged per proyecto · ordenadas desc."""
        result = await self.db.scalars(
            select(Alert)
            .where(Alert.project_id == project_id)
            .where(Alert.acknowledged_at.is_(None))
            .order_by(Alert.triggered_at.desc())
        )
        return list(result)

    async def list_active_global(
        self, limit: int = 50,
    ) -> list[Alert]:
        """Alertas activas todos proyectos (admin Marcos · top N recientes)."""
        result = await self.db.scalars(
            select(Alert)
            .where(Alert.acknowledged_at.is_(None))
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
        )
        return list(result)

    async def acknowledge(
        self, alert_id: UUID, user_id: UUID | None = None,
    ) -> bool:
        """Marca alert como acknowledged · idempotente (False si ya ack)."""
        result = await self.db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .where(Alert.acknowledged_at.is_(None))
            .values(
                acknowledged_at=datetime.now(timezone.utc),
                acknowledged_by=user_id,
            )
        )
        return result.rowcount > 0
