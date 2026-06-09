"""Dead Letter Queue service · Sesión 3B-2B.11 Ejecutable 6 Phase 11.3 (2026-05-27).

DLQ implementation OPS-026 DRY · ADR-025 sostained · reuses existing
``NotificationEvent`` table:
- ``status='failed'`` AND ``retry_count >= MAX_RETRIES`` = DLQ entry semantically
- NO new table needed (briefing scope refined post alembic multi-head DEFER state)
- Existing columns cover all DLQ metadata: error · channels_attempted · channels_failed

Pure functional service · pure read queries + atomic reprocess action.

audit_log emit (Sub-atom 5.A 3-way OR):
- notification.dlq.viewed
- notification.dlq.reprocessed
- notification.dlq.resolved
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


MAX_RETRIES = 3
"""Threshold de retries failed para considerar event como DLQ entry.

Celery max_retries=3 + countdown=60 per task.py existing. Si event final
status='failed' AND retry_count >= 3 → DLQ semantically.
"""

NOTIFICATION_DLQ_PERSISTED = "notification.dlq.persisted"
NOTIFICATION_DLQ_VIEWED = "notification.dlq.viewed"
NOTIFICATION_DLQ_REPROCESSED = "notification.dlq.reprocessed"
NOTIFICATION_DLQ_RESOLVED = "notification.dlq.resolved"


@dataclass
class DlqEntry:
    """Single DLQ entry · derived from NotificationEvent failed row.

    JSON-serializable via asdict (or to_dict).
    """

    event_id: str
    event_type: str
    recipient_email: str
    project_id: Optional[str]
    status: str
    retry_count: int
    error: Optional[str]
    channels_attempted: list
    channels_failed: list
    template_used: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DlqSummary:
    """Summary count breakdown for admin dashboard widget."""

    total_count: int
    last_24h_count: int
    by_event_type: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)


async def list_dlq_entries(
    db: AsyncSession,
    *,
    project_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[DlqEntry]:
    """Query failed notification events con retry_count >= MAX_RETRIES.

    Ordered by created_at DESC (newest first).
    Optional project_id filter scope.
    """
    sql_parts = [
        "SELECT id, event_type, recipient_email, project_id, status, retry_count, "
        "error, channels_attempted, channels_failed, template_used, "
        "created_at, updated_at "
        "FROM notification_events "
        "WHERE status = 'failed' AND retry_count >= :max_retries "
        "AND deleted_at IS NULL"
    ]
    params: dict = {"max_retries": MAX_RETRIES, "limit": limit, "offset": offset}
    if project_id is not None:
        sql_parts.append("AND project_id = :pid")
        params["pid"] = str(project_id)
    sql_parts.append("ORDER BY created_at DESC LIMIT :limit OFFSET :offset")

    rows = (await db.execute(sa_text(" ".join(sql_parts)), params)).all()

    entries: list[DlqEntry] = []
    for r in rows:
        (event_id, event_type, recipient_email, project_id_row, status,
         retry_count, error, channels_attempted, channels_failed,
         template_used, created_at, updated_at) = r
        entries.append(DlqEntry(
            event_id=str(event_id),
            event_type=event_type,
            recipient_email=recipient_email,
            project_id=str(project_id_row) if project_id_row else None,
            status=status,
            retry_count=int(retry_count),
            error=error,
            channels_attempted=channels_attempted or [],
            channels_failed=channels_failed or [],
            template_used=template_used,
            created_at=created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
            updated_at=updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
        ))
    return entries


async def get_dlq_summary(
    db: AsyncSession,
    *,
    project_id: Optional[uuid.UUID] = None,
) -> DlqSummary:
    """Aggregated summary count + 24h delta + by event_type breakdown."""
    pid_clause = "AND project_id = :pid" if project_id is not None else ""
    params: dict = {"max_retries": MAX_RETRIES}
    if project_id is not None:
        params["pid"] = str(project_id)

    total_row = (await db.execute(sa_text(
        f"SELECT COUNT(*) FROM notification_events "
        f"WHERE status = 'failed' AND retry_count >= :max_retries "
        f"AND deleted_at IS NULL {pid_clause}"
    ), params)).first()
    total = int(total_row[0]) if total_row else 0

    last_24h_row = (await db.execute(sa_text(
        f"SELECT COUNT(*) FROM notification_events "
        f"WHERE status = 'failed' AND retry_count >= :max_retries "
        f"AND deleted_at IS NULL AND created_at >= now() - interval '24 hours' "
        f"{pid_clause}"
    ), params)).first()
    last_24h = int(last_24h_row[0]) if last_24h_row else 0

    by_type_rows = (await db.execute(sa_text(
        f"SELECT event_type, COUNT(*) FROM notification_events "
        f"WHERE status = 'failed' AND retry_count >= :max_retries "
        f"AND deleted_at IS NULL {pid_clause} "
        f"GROUP BY event_type ORDER BY COUNT(*) DESC LIMIT 10"
    ), params)).all()
    by_type = {row[0]: int(row[1]) for row in by_type_rows}

    return DlqSummary(
        total_count=total,
        last_24h_count=last_24h,
        by_event_type=by_type,
    )


async def reprocess_dlq_entry(
    db: AsyncSession,
    event_id: uuid.UUID,
    *,
    usuario: Optional[str] = None,
) -> dict:
    """Mark DLQ entry as queued + reset retry_count · re-dispatch via Celery worker.

    Atomic UPDATE protects against concurrent reprocess (race-safe via WHERE
    status='failed' guard). Returns count of rows affected (0 si NO existe O
    ya reprocessed by other worker).

    audit_log emit notification.dlq.reprocessed Sub-atom 5.A 3-way OR.
    """
    row = (await db.execute(sa_text(
        "SELECT project_id FROM notification_events WHERE id = :eid"
    ), {"eid": str(event_id)})).first()
    if row is None:
        return {"reprocessed": False, "reason": "not_found"}
    project_id = row[0]

    result = await db.execute(sa_text(
        "UPDATE notification_events "
        "SET status = 'queued', retry_count = 0, error = NULL, updated_at = now() "
        "WHERE id = :eid AND status = 'failed' AND retry_count >= :max_retries"
    ), {"eid": str(event_id), "max_retries": MAX_RETRIES})
    affected = result.rowcount

    if affected > 0:
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'notification_events', :eid, "
            ":accion, :user, :pid, :payload, now())"
        ), {
            "eid": str(event_id),
            "accion": NOTIFICATION_DLQ_REPROCESSED,
            "user": usuario or "system",
            "pid": str(project_id) if project_id else None,
            "payload": json.dumps({"event_id": str(event_id)}),
        })

    return {"reprocessed": affected > 0, "rows_affected": affected}


async def resolve_dlq_entry(
    db: AsyncSession,
    event_id: uuid.UUID,
    *,
    resolution_note: str,
    usuario: Optional[str] = None,
) -> dict:
    """Mark DLQ entry as resolved manual · soft-delete (deleted_at = now).

    Audit emit notification.dlq.resolved Sub-atom 5.A.
    """
    row = (await db.execute(sa_text(
        "SELECT project_id FROM notification_events WHERE id = :eid"
    ), {"eid": str(event_id)})).first()
    if row is None:
        return {"resolved": False, "reason": "not_found"}
    project_id = row[0]

    result = await db.execute(sa_text(
        "UPDATE notification_events "
        "SET deleted_at = now(), "
        "error = COALESCE(error, '') || ' [resolved: ' || :note || ']', "
        "updated_at = now() "
        "WHERE id = :eid AND status = 'failed' AND deleted_at IS NULL"
    ), {"eid": str(event_id), "note": resolution_note})
    affected = result.rowcount

    if affected > 0:
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'notification_events', :eid, "
            ":accion, :user, :pid, :payload, now())"
        ), {
            "eid": str(event_id),
            "accion": NOTIFICATION_DLQ_RESOLVED,
            "user": usuario or "system",
            "pid": str(project_id) if project_id else None,
            "payload": json.dumps({"resolution_note": resolution_note}),
        })

    return {"resolved": affected > 0, "rows_affected": affected}
