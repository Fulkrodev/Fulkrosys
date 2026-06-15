"""Celery tasks for Motor 26 scheduled backup operations.

Usa celery_app (Sprint C5). Stub si Celery no está instalado (dev/tests).
"""
import subprocess
from datetime import datetime, timezone

from loguru import logger

from backend.app.core.celery_app import celery_app

# Alias compat con patrón original @shared_task
shared_task = celery_app.task


@shared_task(name="backup.run_pgbackrest_full")
def run_pgbackrest_full(job_id: str | None = None) -> dict:  # pragma: no cover
    """Execute a full PostgreSQL backup via pgBackRest.

    Scheduled: weekly (Sunday 02:00 via Celery beat).
    """
    logger.info("Starting pgBackRest full backup")
    try:
        result = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "--type=full", "backup"],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
        )
        if result.returncode != 0:
            logger.error("pgBackRest full backup failed: {}", result.stderr)
            return {"status": "failed", "error": result.stderr[:500]}

        # Get backup info
        info_result = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "--output=json", "info"],
            capture_output=True,
            text=True,
        )

        logger.info("pgBackRest full backup completed successfully")
        return {
            "status": "completed",
            "type": "postgres_full",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "info": info_result.stdout[:2000] if info_result.returncode == 0 else None,
        }
    except subprocess.TimeoutExpired:
        logger.error("pgBackRest full backup timed out after 1 hour")
        return {"status": "failed", "error": "timeout"}
    except FileNotFoundError:
        logger.warning("pgBackRest not installed — skipping backup (dev mode)")
        return {"status": "skipped", "reason": "pgbackrest not installed"}


@shared_task(name="backup.run_pgbackrest_incremental")
def run_pgbackrest_incremental(job_id: str | None = None) -> dict:  # pragma: no cover
    """Execute an incremental PostgreSQL backup.

    Scheduled: daily at 03:00 via Celery beat.
    """
    logger.info("Starting pgBackRest incremental backup")
    try:
        result = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "--type=incr", "backup"],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if result.returncode != 0:
            logger.error("pgBackRest incremental backup failed: {}", result.stderr)
            return {"status": "failed", "error": result.stderr[:500]}

        logger.info("pgBackRest incremental backup completed")
        return {"status": "completed", "type": "postgres_incremental"}
    except FileNotFoundError:
        return {"status": "skipped", "reason": "pgbackrest not installed"}


@shared_task(name="backup.verify_integrity")
def verify_backup_integrity(check_id: str | None = None) -> dict:  # pragma: no cover
    """Verify integrity of the latest backup.

    Scheduled: weekly after full backup.
    """
    logger.info("Starting backup integrity verification")
    try:
        result = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "verify"],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        passed = result.returncode == 0
        logger.info("Backup integrity verification: {}", "passed" if passed else "FAILED")
        return {
            "status": "passed" if passed else "failed",
            "output": result.stdout[:1000],
        }
    except FileNotFoundError:
        return {"status": "skipped", "reason": "pgbackrest not installed"}


@shared_task(name="backup.monthly_restore_test")
def monthly_restore_test(test_id: str | None = None) -> dict:  # pragma: no cover
    """Monthly automated restore test.

    Per v2.1 Parte 4.2: the platform restores itself on a temporary
    server, validates it boots, destroys the temp server, and logs results.

    Future hardening (post-Hetzner provisioning): orchestrate with
    Terraform + Ansible the five-step flow:
      1. Spin up ephemeral Hetzner server
      2. Restore latest backup
      3. Run health checks
      4. Destroy ephemeral server
      5. Record results
    """
    logger.info("Monthly restore test triggered (test_id={})", test_id)
    return {
        "status": "scheduled",
        "test_id": test_id,
        "message": "Pending Hetzner provisioning — orchestration with Terraform + Ansible",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@shared_task(name="backup.run_dr_drill")
def run_dr_drill(drill_id: str | None = None) -> dict:  # pragma: no cover
    """Disaster Recovery drill orchestrator.

    Triggered by ``POST /backup/dr-drills``. The full drill (failover to
    DR site, validation, failback) requires the Hetzner Terraform stack;
    until then this task records the request so the operator can track
    the run via the Operations dashboard.
    """
    logger.info("DR drill triggered (drill_id={})", drill_id)
    return {
        "status": "scheduled",
        "drill_id": drill_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
