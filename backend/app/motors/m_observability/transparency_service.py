"""AI Act art.50 transparency service · sub-atom 1.E.1.B.2.

Helper service-to-service para registrar decisiones IA externalizadas
con purpose statement cliente-readable + retention boundary.

Reglas:
  - R29 firmísimo cliente · purpose statement friendly explainer
  - retention_until = today + 6 years per AI Act guidance
  - cliente solo ve eventos de SU proyecto (RLS project-scoped)
  - admin via fulkro_migrate role ve full cross-project access
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, select, text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_observability.models import AIActTransparencyEvent


async def _elevate_admin(db: AsyncSession) -> None:
    """FIX(RLS): la vista admin del log AI-Act es cross-cliente. La ruta admin
    (require_owner) NO fija tenant context → bajo fulkro_app
    ai_act_transparency_events (RLS) devolvía vacío para Marcos. Elevar a
    fulkro_app_bypassrls (transaction-scoped). La ruta cliente NO usa esto (filtra
    por client_id con el rol ya bypaseado por verify_session)."""
    await db.execute(_sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))


# Retention boundary · AI Act art.50 guidance 6 years
# (mismo cement que ENS audit_log + RGPD prescripción art.83.5).
_RETENTION_YEARS = 6


def _compute_retention_until(at: Optional[datetime] = None) -> date:
    """retention_until = at::date + 6 years (defensible audit boundary)."""
    now = at or datetime.now(timezone.utc)
    target_year = now.year + _RETENTION_YEARS
    # Defensive · si Feb 29 + 6y → cae en año no-bisiesto · use Feb 28.
    day = now.day
    month = now.month
    if month == 2 and day == 29:
        try:
            return date(target_year, 2, 29)
        except ValueError:
            return date(target_year, 2, 28)
    return date(target_year, month, day)


@dataclass(frozen=True)
class TransparencyLogResult:
    """Aggregate response per project/client log."""

    items: list[dict]
    total: int
    days: int


async def log_transparency_event(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    event_type: str,
    llm_provider: str,
    llm_model: str,
    agent_name: str,
    purpose: str,
    client_id: Optional[uuid.UUID] = None,
    artifact_type: Optional[str] = None,
    artifact_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict] = None,
) -> AIActTransparencyEvent:
    """Insert one transparency event · returns persisted entity.

    Service-to-service helper · llamado desde agents post-generation de
    deliverable/proposal/etc. Commits explícito (LECCIÓN-OPS-043).
    """
    event = AIActTransparencyEvent(
        project_id=project_id,
        client_id=client_id,
        event_type=event_type,
        llm_provider=llm_provider,
        llm_model=llm_model[:128],
        agent_name=agent_name[:64],
        artifact_type=artifact_type[:64] if artifact_type else None,
        artifact_id=artifact_id,
        purpose=purpose[:256],
        metadata_=metadata,
        retention_until=_compute_retention_until(),
    )
    db.add(event)
    await db.flush()
    await db.commit()
    return event


async def get_project_transparency_log(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    days: int = 180,
    limit: int = 200,
) -> TransparencyLogResult:
    """Admin full view · all events per project over last N days.

    Returns ordered DESC by created_at · capped at limit.
    """
    await _elevate_admin(db)
    days = max(1, min(int(days), 730))
    limit = max(1, min(int(limit), 1000))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(AIActTransparencyEvent)
        .where(
            AIActTransparencyEvent.project_id == project_id,
            AIActTransparencyEvent.created_at > cutoff,
        )
        .order_by(desc(AIActTransparencyEvent.created_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    items = [
        {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "client_id": str(row.client_id) if row.client_id else None,
            "event_type": row.event_type,
            "llm_provider": row.llm_provider,
            "llm_model": row.llm_model,
            "agent_name": row.agent_name,
            "artifact_type": row.artifact_type,
            "artifact_id": str(row.artifact_id) if row.artifact_id else None,
            "purpose": row.purpose,
            "metadata": row.metadata_,
            "retention_until": row.retention_until.isoformat(),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return TransparencyLogResult(items=items, total=len(items), days=days)


async def get_client_transparency_log(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    days: int = 180,
    limit: int = 200,
) -> TransparencyLogResult:
    """Cliente portal view · cross-project events for one client.

    Returns ordered DESC · capped. Cliente-facing fields only · NO leak
    metadata sensitive · NO leak llm_provider/llm_model technical details
    (caller decides exposure via response schema mapping).
    """
    days = max(1, min(int(days), 730))
    limit = max(1, min(int(limit), 1000))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(AIActTransparencyEvent)
        .where(
            AIActTransparencyEvent.client_id == client_id,
            AIActTransparencyEvent.created_at > cutoff,
        )
        .order_by(desc(AIActTransparencyEvent.created_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    # Cliente-facing view · R29 friendly · NO leak technical details
    items = [
        {
            "id": str(row.id),
            "event_type": row.event_type,
            "agent_name": row.agent_name,
            "artifact_type": row.artifact_type,
            "artifact_id": (
                str(row.artifact_id) if row.artifact_id else None
            ),
            "purpose": row.purpose,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return TransparencyLogResult(items=items, total=len(items), days=days)
