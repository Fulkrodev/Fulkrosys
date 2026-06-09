"""Tests del service core Motor 26 — Backup & DR Engine.

Platform-global tables (no RLS, no tenant context needed).
Tests use unique prefixes to isolate from seed data.
"""
import pytest
from uuid import uuid4


from backend.app.motors.m26_backup.service import BackupService
from backend.app.motors.m26_backup.exceptions import (
    BackupJobNotFoundError,
)


# ================================================================
# BACKUP JOBS (Tests 1-6)
# ================================================================

class TestBackupJobs:

    @pytest.mark.asyncio
    async def test_create_backup_job(self, db):
        """Test 1: Create backup job returns pending status."""
        svc = BackupService(db)
        job = await svc.create_backup_job(backup_type="postgres_full")
        await db.flush()
        assert job.id is not None
        assert job.backup_type == "postgres_full"
        assert job.status == "pending"
        assert job.started_at is None

    @pytest.mark.asyncio
    async def test_start_backup_job(self, db):
        """Test 2: Start marks job as running with timestamp."""
        svc = BackupService(db)
        job = await svc.create_backup_job(backup_type="postgres_full")
        await db.flush()

        started = await svc.start_backup(job.id)
        assert started.status == "running"
        assert started.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_backup_job_success(self, db):
        """Test 3: Complete marks job as completed with hash."""
        svc = BackupService(db)
        job = await svc.create_backup_job(backup_type="postgres_full")
        await db.flush()
        await svc.start_backup(job.id)

        completed = await svc.complete_backup(
            job.id, size_bytes=1024000, hash_sha256="abc123def456"
        )
        assert completed.status == "completed"
        assert completed.size_bytes == 1024000
        assert completed.hash_sha256 == "abc123def456"
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_backup_job_failure(self, db):
        """Test 4: Complete with error marks as failed."""
        svc = BackupService(db)
        job = await svc.create_backup_job(backup_type="postgres_full")
        await db.flush()

        failed = await svc.complete_backup(
            job.id, size_bytes=0, hash_sha256="",
            error_message="pgBackRest timeout"
        )
        assert failed.status == "failed"
        assert failed.error_message == "pgBackRest timeout"

    @pytest.mark.asyncio
    async def test_start_nonexistent_job_raises(self, db):
        """Test 5: Start nonexistent job raises BackupJobNotFoundError."""
        svc = BackupService(db)
        with pytest.raises(BackupJobNotFoundError):
            await svc.start_backup(uuid4())

    @pytest.mark.asyncio
    async def test_list_backup_jobs_filtered(self, db):
        """Test 6: List jobs with type filter."""
        svc = BackupService(db)
        await svc.create_backup_job(backup_type="test_minio_snapshot")
        await svc.create_backup_job(backup_type="test_minio_snapshot")
        await svc.create_backup_job(backup_type="test_config_snapshot")
        await db.flush()

        minio_jobs = await svc.list_backup_jobs(backup_type="test_minio_snapshot")
        assert len(minio_jobs) >= 2


# ================================================================
# RETENTION POLICIES (Tests 7-8)
# ================================================================

class TestRetentionPolicies:

    @pytest.mark.asyncio
    async def test_upsert_creates_policy(self, db):
        """Test 7: Upsert creates new policy."""
        svc = BackupService(db)
        unique_type = f"test_type_{uuid4().hex[:8]}"
        policy = await svc.upsert_retention_policy(
            backup_type=unique_type,
            daily_keep=7, weekly_keep=4, monthly_keep=12, yearly_keep=5,
        )
        await db.flush()
        assert policy.backup_type == unique_type
        assert policy.daily_keep == 7

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, db):
        """Test 8: Upsert updates existing policy."""
        svc = BackupService(db)
        unique_type = f"test_type_{uuid4().hex[:8]}"
        await svc.upsert_retention_policy(backup_type=unique_type, daily_keep=7)
        await db.flush()

        updated = await svc.upsert_retention_policy(backup_type=unique_type, daily_keep=30)
        await db.flush()
        assert updated.daily_keep == 30


# ================================================================
# RESTORE TESTS (Tests 9-10)
# ================================================================

class TestRestoreTests:

    @pytest.mark.asyncio
    async def test_create_restore_test(self, db):
        """Test 9: Create restore test."""
        svc = BackupService(db)
        test = await svc.create_restore_test(test_type="full_db")
        await db.flush()
        assert test.test_type == "full_db"
        assert test.status == "pending"

    @pytest.mark.asyncio
    async def test_complete_restore_test_passed(self, db):
        """Test 10: Complete restore test as passed."""
        svc = BackupService(db)
        test = await svc.create_restore_test(test_type="full_db")
        await db.flush()

        completed = await svc.complete_restore_test(
            test.id,
            rto_seconds=120,
            validation_report={"all_checks_passed": True, "tables_verified": 82},
        )
        assert completed.status == "passed"
        assert completed.rto_seconds == 120


# ================================================================
# DR DRILLS (Tests 11-12)
# ================================================================

class TestDrDrills:

    @pytest.mark.asyncio
    async def test_create_dr_drill(self, db):
        """Test 11: Create DR drill with objectives."""
        svc = BackupService(db)
        drill = await svc.create_dr_drill(
            rto_objective_seconds=14400,
            rpo_objective_seconds=86400,
        )
        await db.flush()
        assert drill.status == "planned"
        assert drill.rto_objective_seconds == 14400

    @pytest.mark.asyncio
    async def test_complete_dr_drill_pass_fail(self, db):
        """Test 12: DR drill pass/fail based on RTO/RPO objectives."""
        svc = BackupService(db)
        drill = await svc.create_dr_drill(
            rto_objective_seconds=14400,
            rpo_objective_seconds=86400,
        )
        await db.flush()

        # Pass case: actual < objective
        completed = await svc.complete_dr_drill(
            drill.id,
            rto_actual_seconds=10000,
            rpo_actual_seconds=3600,
            report_path="/reports/dr_drill_test.pdf",
        )
        assert completed.status == "passed"


# ================================================================
# INTEGRITY VERIFICATION (Tests 13-14)
# ================================================================

class TestIntegrityVerification:

    @pytest.mark.asyncio
    async def test_create_integrity_check(self, db):
        """Test 13: Create integrity check."""
        svc = BackupService(db)
        check = await svc.create_integrity_check(
            verification_type="hash_sampling", sample_size=50
        )
        await db.flush()
        assert check.verification_type == "hash_sampling"
        assert check.sample_size == 50

    @pytest.mark.asyncio
    async def test_complete_integrity_check_clean(self, db):
        """Test 14: Integrity check with zero discrepancies passes."""
        svc = BackupService(db)
        check = await svc.create_integrity_check(
            verification_type="hash_sampling"
        )
        await db.flush()

        completed = await svc.complete_integrity_check(
            check.id,
            discrepancies_found=0,
            report={"sampled": 100, "verified": 100},
        )
        assert completed.status == "passed"
        assert completed.discrepancies_found == 0


# ================================================================
# DASHBOARD STATUS (Tests 15-16)
# ================================================================

class TestDashboardStatus:

    @pytest.mark.asyncio
    async def test_get_status_returns_health(self, db):
        """Test 15: Status returns health semaphore."""
        svc = BackupService(db)
        status = await svc.get_backup_status()
        assert "health" in status
        assert status["health"] in ("green", "yellow", "red")

    @pytest.mark.asyncio
    async def test_health_green_after_recent_backup(self, db):
        """Test 16: Health green after recent completed backup + restore test."""
        svc = BackupService(db)
        # Create fresh completed backup
        job = await svc.create_backup_job(backup_type="postgres_full")
        await db.flush()
        await svc.start_backup(job.id)
        await svc.complete_backup(job.id, size_bytes=5000, hash_sha256="test")
        await db.flush()

        # Create passed restore test
        test = await svc.create_restore_test(test_type="full_db")
        await db.flush()
        await svc.complete_restore_test(
            test.id, rto_seconds=60,
            validation_report={"all_checks_passed": True},
        )
        await db.flush()

        status = await svc.get_backup_status()
        assert status["health"] == "green"
