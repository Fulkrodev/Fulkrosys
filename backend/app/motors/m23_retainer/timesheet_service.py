"""Timesheet service · MB-7.bis atom 7.bis.5 Q6.C.

Tracking horas Marcos cross-cliente (auto-track + manual override).
Used by CapacityTile (RetainerOpsCenter) y /admin/timesheet UI.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m23_retainer.timesheet_models import (
    MarcosTimesheetEntry,
)


@dataclass
class TimesheetEntryOut:
    id: str
    client_id: str
    retainer_id: Optional[str]
    activity_id: Optional[str]
    started_at: str
    ended_at: Optional[str]
    duration_minutes: Optional[int]
    source: str
    manual_override: bool
    endpoint_path: Optional[str]
    notes: Optional[str]


@dataclass
class ClientHoursSummary:
    client_id: str
    client_name: str
    total_minutes: int


class TimesheetService:
    """6 methods · MB-7.bis atom 7.bis.5."""

    async def start_session(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        retainer_id: Optional[uuid.UUID] = None,
        activity_id: Optional[uuid.UUID] = None,
        endpoint_path: Optional[str] = None,
        source: str = "auto_endpoint",
    ) -> MarcosTimesheetEntry:
        """Create an open session · ended_at NULL until end_session."""
        entry = MarcosTimesheetEntry(
            client_id=client_id,
            retainer_id=retainer_id,
            activity_id=activity_id,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            duration_minutes=None,
            source=source,
            endpoint_path=endpoint_path,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def end_session(
        self,
        db: AsyncSession,
        entry_id: uuid.UUID,
        *,
        notes: Optional[str] = None,
    ) -> Optional[MarcosTimesheetEntry]:
        """Close an open session · compute duration_minutes."""
        entry = (await db.execute(
            select(MarcosTimesheetEntry).where(
                MarcosTimesheetEntry.id == entry_id,
                MarcosTimesheetEntry.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if not entry:
            return None
        if entry.ended_at is not None:
            return entry  # idempotent
        entry.ended_at = datetime.now(timezone.utc)
        delta = entry.ended_at - entry.started_at
        entry.duration_minutes = max(0, int(delta.total_seconds() / 60))
        if notes:
            entry.notes = (entry.notes or "") + notes
        await db.flush()
        return entry

    async def add_manual_entry(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        started_at: datetime,
        duration_minutes: int,
        retainer_id: Optional[uuid.UUID] = None,
        activity_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> MarcosTimesheetEntry:
        """Create a fully-formed manual entry (already ended)."""
        ended_at = started_at + timedelta(minutes=duration_minutes)
        entry = MarcosTimesheetEntry(
            client_id=client_id,
            retainer_id=retainer_id,
            activity_id=activity_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_minutes=duration_minutes,
            source="manual",
            manual_override=True,
            notes=notes,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def get_entries_filtered(
        self,
        db: AsyncSession,
        *,
        client_id: Optional[uuid.UUID] = None,
        retainer_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarcosTimesheetEntry]:
        stmt = select(MarcosTimesheetEntry).where(
            MarcosTimesheetEntry.deleted_at.is_(None),
        )
        if client_id is not None:
            stmt = stmt.where(MarcosTimesheetEntry.client_id == client_id)
        if retainer_id is not None:
            stmt = stmt.where(MarcosTimesheetEntry.retainer_id == retainer_id)
        if since is not None:
            stmt = stmt.where(MarcosTimesheetEntry.started_at >= since)
        if until is not None:
            stmt = stmt.where(MarcosTimesheetEntry.started_at <= until)
        stmt = stmt.order_by(
            MarcosTimesheetEntry.started_at.desc(),
        ).limit(int(limit)).offset(int(offset))
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)

    async def get_top_clients_by_hours(
        self,
        db: AsyncSession,
        *,
        limit: int = 3,
        since: Optional[datetime] = None,
    ) -> list[ClientHoursSummary]:
        """Top N clients ordered by total minutes (descending)."""
        cutoff_clause = ""
        params: dict = {"lim": int(limit)}
        if since is not None:
            cutoff_clause = "AND mt.started_at >= :cutoff"
            params["cutoff"] = since
        rows = (await db.execute(
            text(
                "SELECT mt.client_id, c.nombre, "
                "COALESCE(SUM(mt.duration_minutes), 0) AS total "
                "FROM marcos_timesheet_entries mt "
                "JOIN clients c ON c.id = mt.client_id "
                "WHERE mt.deleted_at IS NULL "
                "AND mt.duration_minutes IS NOT NULL "
                f"{cutoff_clause} "
                "GROUP BY mt.client_id, c.nombre "
                "ORDER BY total DESC LIMIT :lim"
            ),
            params,
        )).mappings().all()
        return [
            ClientHoursSummary(
                client_id=str(r["client_id"]),
                client_name=r["nombre"],
                total_minutes=int(r["total"]),
            )
            for r in rows
        ]

    async def get_monthly_total_minutes(
        self, db: AsyncSession,
    ) -> int:
        """Total minutes recorded this calendar month."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )
        row = (await db.execute(text(
            "SELECT COALESCE(SUM(duration_minutes), 0) "
            "FROM marcos_timesheet_entries "
            "WHERE deleted_at IS NULL "
            "AND duration_minutes IS NOT NULL "
            "AND started_at >= :cutoff"
        ), {"cutoff": month_start})).first()
        return int(row[0]) if row else 0
