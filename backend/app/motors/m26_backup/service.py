"""Motor 26 — Backup & Disaster Recovery service.

Responsible for:
- pgBackRest full/incremental/WAL backups
- MinIO mirror snapshots
- Integrity verification (hash sampling)
- Automated restore tests (monthly)
- DR drills (quarterly)
- Retention policy enforcement

Per v2.1 §9.13: built in weeks 4-6, BEFORE ingesting real client data.
Exit criteria: at least one verified full backup + one passed restore test.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.backup import (
    BackupJob,
    BackupRetentionPolicy,
    BackupRestoreTest,
    DrDrill,
    IntegrityVerification,
)
from backend.app.motors.m26_backup.exceptions import (
    BackupJobNotFoundError,
    RestoreTestNotFoundError,
    DrDrillNotFoundError,
    IntegrityVerificationNotFoundError,
)
from backend.app.config import get_settings

settings = get_settings()


class BackupService:
    """Orchestrates all backup & DR operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Backup Jobs ─────────────────────────────────────────

    async def create_backup_job(
        self,
        backup_type: str,
        location: str | None = None,
    ) -> BackupJob:
        """Register a new backup job (pending execution)."""
        job = BackupJob(
            backup_type=backup_type,
            status="pending",
            location=location or self._default_location(backup_type),
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def start_backup(self, job_id: uuid.UUID) -> BackupJob:
        """Mark a backup job as started."""
        job = await self.db.get(BackupJob, job_id)
        if not job:
            raise BackupJobNotFoundError(f"Backup job {job_id} not found")
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await self.db.flush()
        return job

    async def complete_backup(
        self,
        job_id: uuid.UUID,
        size_bytes: int,
        hash_sha256: str,
        error_message: str | None = None,
    ) -> BackupJob:
        """Mark a backup job as completed (success or failure)."""
        job = await self.db.get(BackupJob, job_id)
        if not job:
            raise BackupJobNotFoundError(f"Backup job {job_id} not found")
        job.completed_at = datetime.now(timezone.utc)
        job.size_bytes = size_bytes
        job.hash_sha256 = hash_sha256
        if error_message:
            job.status = "failed"
            job.error_message = error_message
        else:
            job.status = "completed"
        await self.db.flush()
        return job

    async def get_latest_backup(self, backup_type: str) -> BackupJob | None:
        """Get the most recent completed backup of a given type."""
        result = await self.db.execute(
            select(BackupJob)
            .where(BackupJob.backup_type == backup_type)
            .where(BackupJob.status == "completed")
            .order_by(BackupJob.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_backup_jobs(
        self,
        backup_type: str | None = None,
        limit: int = 50,
    ) -> list[BackupJob]:
        """List backup jobs, optionally filtered by type."""
        query = select(BackupJob).order_by(BackupJob.created_at.desc()).limit(limit)
        if backup_type:
            query = query.where(BackupJob.backup_type == backup_type)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Retention Policies ──────────────────────────────────

    async def list_retention_policies(self) -> list[BackupRetentionPolicy]:
        """List all retention policies (platform-global)."""
        result = await self.db.execute(
            select(BackupRetentionPolicy).order_by(BackupRetentionPolicy.backup_type)
        )
        return list(result.scalars().all())

    async def get_retention_policy(self, backup_type: str) -> BackupRetentionPolicy | None:
        """Get the retention policy for a backup type."""
        result = await self.db.execute(
            select(BackupRetentionPolicy).where(
                BackupRetentionPolicy.backup_type == backup_type
            )
        )
        return result.scalar_one_or_none()

    async def upsert_retention_policy(
        self,
        backup_type: str,
        daily_keep: int = 30,
        weekly_keep: int = 12,
        monthly_keep: int = 12,
        yearly_keep: int = 3,
    ) -> BackupRetentionPolicy:
        """Create or update a retention policy."""
        existing = await self.get_retention_policy(backup_type)
        if existing:
            existing.daily_keep = daily_keep
            existing.weekly_keep = weekly_keep
            existing.monthly_keep = monthly_keep
            existing.yearly_keep = yearly_keep
            await self.db.flush()
            return existing
        policy = BackupRetentionPolicy(
            backup_type=backup_type,
            daily_keep=daily_keep,
            weekly_keep=weekly_keep,
            monthly_keep=monthly_keep,
            yearly_keep=yearly_keep,
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def seed_default_policies(self) -> list[BackupRetentionPolicy]:
        """Seed default retention policies per v2.1 Parte 4.2."""
        defaults = [
            ("postgres_full", 30, 12, 12, 3),
            ("postgres_incremental", 30, 12, 12, 3),
            ("postgres_wal", 7, 4, 0, 0),
            ("minio_snapshot", 30, 12, 12, 3),
            ("config_snapshot", 30, 12, 12, 3),
            ("audit_log_export", 0, 0, 12, 7),  # audit logs kept longer
        ]
        policies = []
        for btype, d, w, m, y in defaults:
            p = await self.upsert_retention_policy(btype, d, w, m, y)
            policies.append(p)
        return policies

    # ── Restore Tests ───────────────────────────────────────

    async def list_restore_tests(self, limit: int = 20) -> list[BackupRestoreTest]:
        """List recent restore tests (platform-global)."""
        result = await self.db.execute(
            select(BackupRestoreTest)
            .order_by(BackupRestoreTest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_restore_test(
        self,
        test_type: str,
        backup_job_id: uuid.UUID | None = None,
    ) -> BackupRestoreTest:
        """Register a new restore test."""
        test = BackupRestoreTest(
            test_type=test_type,
            backup_job_id=backup_job_id,
            status="pending",
        )
        self.db.add(test)
        await self.db.flush()
        return test

    async def complete_restore_test(
        self,
        test_id: uuid.UUID,
        rto_seconds: int,
        validation_report: dict,
        sandbox_destroyed: bool = True,
    ) -> BackupRestoreTest:
        """Record restore test completion."""
        test = await self.db.get(BackupRestoreTest, test_id)
        if not test:
            raise RestoreTestNotFoundError(f"Restore test {test_id} not found")
        test.completed_at = datetime.now(timezone.utc)
        test.rto_seconds = rto_seconds
        test.validation_report = validation_report
        test.sandbox_destroyed = sandbox_destroyed
        test.status = "passed" if validation_report.get("all_checks_passed") else "failed"
        await self.db.flush()
        return test

    async def get_last_restore_test(self) -> BackupRestoreTest | None:
        """Get the most recent restore test."""
        result = await self.db.execute(
            select(BackupRestoreTest)
            .order_by(BackupRestoreTest.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── DR Drills ───────────────────────────────────────────

    async def create_dr_drill(
        self,
        rto_objective_seconds: int = 14400,  # 4h per v2.1
        rpo_objective_seconds: int = 86400,  # 24h per v2.1
    ) -> DrDrill:
        """Schedule a new DR drill."""
        drill = DrDrill(
            drill_date=datetime.now(timezone.utc).date(),
            initiated_by="system",
            rto_objective_seconds=rto_objective_seconds,
            rpo_objective_seconds=rpo_objective_seconds,
            status="planned",
        )
        self.db.add(drill)
        await self.db.flush()
        return drill

    async def complete_dr_drill(
        self,
        drill_id: uuid.UUID,
        rto_actual_seconds: int,
        rpo_actual_seconds: int,
        report_path: str,
        issues_found: dict | None = None,
    ) -> DrDrill:
        """Record DR drill completion."""
        drill = await self.db.get(DrDrill, drill_id)
        if not drill:
            raise DrDrillNotFoundError(f"DR drill {drill_id} not found")
        drill.rto_actual_seconds = rto_actual_seconds
        drill.rpo_actual_seconds = rpo_actual_seconds
        drill.report_path = report_path
        drill.issues_found = issues_found or {}
        passed = (
            rto_actual_seconds <= drill.rto_objective_seconds
            and rpo_actual_seconds <= drill.rpo_objective_seconds
        )
        drill.status = "passed" if passed else "failed"
        await self.db.flush()
        return drill

    # ── Integrity Verification ──────────────────────────────

    async def create_integrity_check(
        self,
        verification_type: str,
        sample_size: int = 100,
    ) -> IntegrityVerification:
        """Register a new integrity verification."""
        check = IntegrityVerification(
            verification_type=verification_type,
            status="pending",
            sample_size=sample_size,
        )
        self.db.add(check)
        await self.db.flush()
        return check

    async def complete_integrity_check(
        self,
        check_id: uuid.UUID,
        discrepancies_found: int,
        report: dict,
    ) -> IntegrityVerification:
        """Record integrity check completion."""
        check = await self.db.get(IntegrityVerification, check_id)
        if not check:
            raise IntegrityVerificationNotFoundError(f"Integrity check {check_id} not found")
        check.verified_at = datetime.now(timezone.utc)
        check.discrepancies_found = discrepancies_found
        check.report = report
        check.status = "passed" if discrepancies_found == 0 else "failed"
        await self.db.flush()
        return check

    # ── Dashboard / Status ──────────────────────────────────

    async def get_backup_status(self) -> dict:
        """Get overall backup & DR status for the operations dashboard."""
        latest_full = await self.get_latest_backup("postgres_full")
        latest_incremental = await self.get_latest_backup("postgres_incremental")
        last_restore = await self.get_last_restore_test()

        now = datetime.now(timezone.utc)
        full_age_hours = (
            (now - latest_full.completed_at).total_seconds() / 3600
            if latest_full and latest_full.completed_at
            else None
        )

        return {
            "last_full_backup": {
                "id": str(latest_full.id) if latest_full else None,
                "completed_at": latest_full.completed_at.isoformat() if latest_full and latest_full.completed_at else None,
                "size_bytes": latest_full.size_bytes if latest_full else None,
                "age_hours": round(full_age_hours, 1) if full_age_hours else None,
                "status": latest_full.status if latest_full else "never",
            },
            "last_incremental_backup": {
                "completed_at": latest_incremental.completed_at.isoformat() if latest_incremental and latest_incremental.completed_at else None,
                "status": latest_incremental.status if latest_incremental else "never",
            },
            "last_restore_test": {
                "completed_at": last_restore.completed_at.isoformat() if last_restore and last_restore.completed_at else None,
                "status": last_restore.status if last_restore else "never",
                "rto_seconds": last_restore.rto_seconds if last_restore else None,
            },
            "health": self._evaluate_health(latest_full, last_restore),
        }

    def _evaluate_health(
        self,
        latest_full: BackupJob | None,
        last_restore: BackupRestoreTest | None,
    ) -> str:
        """Evaluate overall backup health: green/yellow/red."""
        if not latest_full or latest_full.status != "completed":
            return "red"
        if not latest_full.completed_at:
            return "red"
        age = datetime.now(timezone.utc) - latest_full.completed_at
        if age > timedelta(days=7):
            return "red"
        if not last_restore or last_restore.status != "passed":
            return "yellow"
        if last_restore.completed_at:
            restore_age = datetime.now(timezone.utc) - last_restore.completed_at
            if restore_age > timedelta(days=35):  # monthly test overdue
                return "yellow"
        return "green"

    # ── Helpers ──────────────────────────────────────────────

    def _default_location(self, backup_type: str) -> str:
        """Generate default backup location path."""
        bucket = settings.backup_s3_bucket
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        return f"s3://{bucket}/{backup_type}/{date_str}"
