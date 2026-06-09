"""Operations overview · admin global aggregator (FASE 9.B / MB-4.D.4).

Endpoint global cross-motor para vista admin Operaciones K.9:
- M26 backups: último completed + counts por status + último restore test
- M25 lifecycle: archivable backups count + grace period activa count
- M27 conformity: próximas renewals ≤ 90 días

NO project-scoped · vista admin Marcos sobre todo el sistema.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


# SEGURIDAD (auditoría 2026-06-07): este router ejecuta SET LOCAL ROLE fulkro_app_bypassrls
# (bypass RLS cross-tenant) y exponía datos de TODOS los proyectos. Era alcanzable
# por cualquier sesión autenticada incl. pool cliente → fuga cross-tenant. Gate
# admin-only obligatorio (ADR-013 require_owner).
router = APIRouter(
    tags=["Operations Overview (FASE 9.B)"],
    dependencies=[Depends(require_owner)],
)


class BackupCounts(BaseModel):
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0


class LastBackupInfo(BaseModel):
    id: str
    backup_type: str
    started_at: str | None
    completed_at: str | None
    size_bytes: int | None
    status: str


class LastRestoreTestInfo(BaseModel):
    id: str
    test_type: str
    started_at: str | None
    completed_at: str | None
    status: str
    rto_seconds: int | None


class UpcomingRenewal(BaseModel):
    project_id: str
    expiration_date: str
    days_until: int
    route_type: str | None


class OperationsOverviewResponse(BaseModel):
    last_backup: LastBackupInfo | None
    backup_counts_30d: BackupCounts
    last_restore_test: LastRestoreTestInfo | None
    archivable_backups_count: int
    archivable_total_size_bytes: int
    grace_period_active_count: int
    upcoming_renewals_90d: list[UpcomingRenewal]
    generated_at: str


@router.get(
    "/operations/overview",
    response_model=OperationsOverviewResponse,
)
async def get_operations_overview(
    db: AsyncSession = Depends(get_db),
) -> OperationsOverviewResponse:
    """Admin global ops overview · M26 + M25 + M27 cross-motor."""
    # Admin role bypass para queries cross-tenant (sesión Marcos)
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # Last backup completed
    last_backup_row = (await db.execute(sa_text(
        """
        SELECT id, backup_type, started_at, completed_at, size_bytes, status
        FROM backup_jobs
        ORDER BY COALESCE(completed_at, started_at, created_at) DESC NULLS LAST
        LIMIT 1
        """,
    ))).mappings().first()

    last_backup: LastBackupInfo | None = None
    if last_backup_row:
        last_backup = LastBackupInfo(
            id=str(last_backup_row["id"]),
            backup_type=last_backup_row["backup_type"],
            started_at=_isofmt(last_backup_row["started_at"]),
            completed_at=_isofmt(last_backup_row["completed_at"]),
            size_bytes=last_backup_row["size_bytes"],
            status=last_backup_row["status"],
        )

    # Backup status counts (last 30 days)
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    counts_rows = (await db.execute(sa_text(
        """
        SELECT status, count(*) AS cnt
        FROM backup_jobs
        WHERE created_at >= :cutoff
        GROUP BY status
        """,
    ), {"cutoff": cutoff_30d})).all()
    counts = BackupCounts()
    for row in counts_rows:
        status = row[0]
        cnt = int(row[1] or 0)
        if status == "pending":
            counts.pending = cnt
        elif status == "running":
            counts.running = cnt
        elif status == "completed":
            counts.completed = cnt
        elif status == "failed":
            counts.failed = cnt

    # Last restore test
    rt_row = (await db.execute(sa_text(
        """
        SELECT id, test_type, started_at, completed_at, status, rto_seconds
        FROM backup_restore_tests
        ORDER BY COALESCE(completed_at, started_at, created_at) DESC NULLS LAST
        LIMIT 1
        """,
    ))).mappings().first()

    last_rt: LastRestoreTestInfo | None = None
    if rt_row:
        last_rt = LastRestoreTestInfo(
            id=str(rt_row["id"]),
            test_type=rt_row["test_type"],
            started_at=_isofmt(rt_row["started_at"]),
            completed_at=_isofmt(rt_row["completed_at"]),
            status=rt_row["status"],
            rto_seconds=rt_row["rto_seconds"],
        )

    # Archivable backups (M25 ProjectArchivedBackup not deleted not expired)
    arch_row = (await db.execute(sa_text(
        """
        SELECT count(*) AS cnt, COALESCE(SUM(zip_size_bytes), 0) AS total_size
        FROM project_archived_backups
        WHERE deleted_at IS NULL
          AND (expires_at IS NULL OR expires_at > now())
        """,
    ))).mappings().first()
    archivable_count = int(arch_row["cnt"] or 0) if arch_row else 0
    archivable_size = int(arch_row["total_size"] or 0) if arch_row else 0

    # Grace period activa (M25 lifecycle · projects in ENDED_CHURN with active grace)
    grace_count = (await db.execute(sa_text(
        """
        SELECT count(*) FROM projects
        WHERE deleted_at IS NULL
          AND grace_period_started_at IS NOT NULL
          AND grace_period_ends_at IS NOT NULL
          AND grace_period_ends_at > now()
        """,
    ))).scalar() or 0

    # Upcoming renewals (M27 conformity_routes expirando ≤ 90 días)
    upcoming_rows = (await db.execute(sa_text(
        """
        SELECT project_id, expiration_date, route_type
        FROM conformity_routes
        WHERE expiration_date IS NOT NULL
          AND expiration_date >= CURRENT_DATE
          AND expiration_date <= CURRENT_DATE + INTERVAL '90 days'
        ORDER BY expiration_date ASC
        LIMIT 50
        """,
    ))).mappings().all()
    today = date.today()
    upcoming: list[UpcomingRenewal] = []
    for row in upcoming_rows:
        exp = row["expiration_date"]
        if isinstance(exp, datetime):
            exp_date = exp.date()
        elif isinstance(exp, date):
            exp_date = exp
        else:
            try:
                exp_date = date.fromisoformat(str(exp))
            except (ValueError, TypeError):
                continue
        upcoming.append(UpcomingRenewal(
            project_id=str(row["project_id"]),
            expiration_date=exp_date.isoformat(),
            days_until=(exp_date - today).days,
            route_type=row.get("route_type"),
        ))

    return OperationsOverviewResponse(
        last_backup=last_backup,
        backup_counts_30d=counts,
        last_restore_test=last_rt,
        archivable_backups_count=archivable_count,
        archivable_total_size_bytes=archivable_size,
        grace_period_active_count=int(grace_count),
        upcoming_renewals_90d=upcoming,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _isofmt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
