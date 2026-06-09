"""Motor 26 — Backup & DR API endpoints.

Platform-global endpoints (no RLS, no tenant context).
Admin-only: all endpoints require Marcos authentication (future).
Patron consistente con M12 Magic Link y M3 DdA Engine.
"""

from fastapi import APIRouter, Depends, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.celery_app import celery_app
from backend.app.database import get_db
from backend.app.motors.m26_backup.service import BackupService
from backend.app.motors.m26_backup.schemas import (
    BackupJobCreate,
    BackupJobOut,
    RetentionPolicyOut,
    RestoreTestCreate,
    RestoreTestOut,
    DrDrillCreate,
    DrDrillOut,
    IntegrityCheckCreate,
    IntegrityCheckOut,
)

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    prefix="/backup", tags=["Motor 26 - Backup & DR"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ================================================================
# ENDPOINT 1: GET /status — Dashboard health
# ================================================================

@router.get("/status")
async def backup_status(db: AsyncSession = Depends(get_db)):
    """Overall backup & DR health status for Operations dashboard."""
    svc = BackupService(db)
    return await svc.get_backup_status()


# ================================================================
# ENDPOINT 2: GET /jobs — List backup jobs
# ================================================================

@router.get("/jobs", response_model=list[BackupJobOut])
async def list_backup_jobs(
    backup_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List recent backup jobs, optionally filtered by type."""
    svc = BackupService(db)
    return await svc.list_backup_jobs(backup_type=backup_type, limit=limit)


# ================================================================
# ENDPOINT 3: POST /jobs — Trigger a backup job
# ================================================================

@router.post("/jobs", response_model=BackupJobOut, status_code=status.HTTP_201_CREATED)
async def trigger_backup(
    body: BackupJobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a new backup job (status=pending).

    The job row is persisted first (audit trail), then dispatched to a
    Celery worker via ``celery_app.send_task``. In dev/tests where Celery
    is not installed, ``send_task`` is a no-op so the API stays functional.
    """
    svc = BackupService(db)
    job = await svc.create_backup_job(
        backup_type=body.backup_type,
        location=body.location,
    )
    await db.commit()
    await db.refresh(job)

    task_name = (
        "backup.run_pgbackrest_full"
        if str(body.backup_type).lower() in ("full", "postgres_full")
        else "backup.run_pgbackrest_incremental"
    )
    try:
        celery_app.send_task(task_name, args=[str(job.id)])
        logger.info("Dispatched {} for job {}", task_name, job.id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Celery dispatch failed for job {}: {}", job.id, exc)

    return job


# ================================================================
# ENDPOINT 4: GET /retention-policies
# ================================================================

@router.get("/retention-policies", response_model=list[RetentionPolicyOut])
async def list_retention_policies(db: AsyncSession = Depends(get_db)):
    """Get all backup retention policies."""
    svc = BackupService(db)
    return await svc.list_retention_policies()


# ================================================================
# ENDPOINT 5: POST /retention-policies/seed
# ================================================================

@router.post("/retention-policies/seed")
async def seed_default_policies(db: AsyncSession = Depends(get_db)):
    """Seed default retention policies per v2.1 Parte 4.2. Idempotent."""
    svc = BackupService(db)
    policies = await svc.seed_default_policies()
    await db.commit()
    return {"seeded": len(policies)}


# ================================================================
# ENDPOINT 6: GET /restore-tests
# ================================================================

@router.get("/restore-tests", response_model=list[RestoreTestOut])
async def list_restore_tests(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get restore test history."""
    svc = BackupService(db)
    return await svc.list_restore_tests(limit=limit)


# ================================================================
# ENDPOINT 7: POST /restore-tests — Create restore test
# ================================================================

@router.post("/restore-tests", response_model=RestoreTestOut, status_code=status.HTTP_201_CREATED)
async def create_restore_test(
    body: RestoreTestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new restore test and dispatch the Celery worker."""
    svc = BackupService(db)
    test = await svc.create_restore_test(
        test_type=body.test_type,
        backup_job_id=body.backup_job_id,
    )
    await db.commit()
    await db.refresh(test)
    try:
        celery_app.send_task("backup.monthly_restore_test", args=[str(test.id)])
        logger.info("Dispatched backup.monthly_restore_test for test {}", test.id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Celery dispatch failed for restore test {}: {}", test.id, exc)
    return test


# ================================================================
# ENDPOINT 8: POST /dr-drills — Create DR drill
# ================================================================

@router.post("/dr-drills", response_model=DrDrillOut, status_code=status.HTTP_201_CREATED)
async def create_dr_drill(
    body: DrDrillCreate,
    db: AsyncSession = Depends(get_db),
):
    """Schedule a new Disaster Recovery drill and dispatch the Celery worker."""
    svc = BackupService(db)
    drill = await svc.create_dr_drill(
        rto_objective_seconds=body.rto_objective_seconds,
        rpo_objective_seconds=body.rpo_objective_seconds,
    )
    await db.commit()
    await db.refresh(drill)
    try:
        celery_app.send_task("backup.run_dr_drill", args=[str(drill.id)])
        logger.info("Dispatched backup.run_dr_drill for drill {}", drill.id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Celery dispatch failed for DR drill {}: {}", drill.id, exc)
    return drill


# ================================================================
# ENDPOINT 9: POST /integrity-checks — Create integrity check
# ================================================================

@router.post("/integrity-checks", response_model=IntegrityCheckOut, status_code=status.HTTP_201_CREATED)
async def create_integrity_check(
    body: IntegrityCheckCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new integrity verification and dispatch the Celery worker."""
    svc = BackupService(db)
    check = await svc.create_integrity_check(
        verification_type=body.verification_type,
        sample_size=body.sample_size,
    )
    await db.commit()
    await db.refresh(check)
    try:
        celery_app.send_task("backup.verify_integrity", args=[str(check.id)])
        logger.info("Dispatched backup.verify_integrity for check {}", check.id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Celery dispatch failed for integrity check {}: {}", check.id, exc)
    return check
