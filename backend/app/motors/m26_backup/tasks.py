"""Celery tasks for Motor 26 scheduled backup operations.

Usa celery_app (Sprint C5). Stub si Celery no está instalado (dev/tests).
"""
import json
import subprocess
from datetime import datetime, timezone

from loguru import logger

from backend.app.core.celery_app import celery_app

# Alias compat con patrón original @shared_task
shared_task = celery_app.task


def _restore_readiness_check() -> dict:
    """I4 (campaña auditoría): verificación REAL de restaurabilidad sin servidor
    efímero. Usa los propios comandos de pgBackRest:
      1. ``pgbackrest check`` valida config + comunicación con el repo + archiving.
      2. ``pgbackrest info --output=json`` confirma que existe ≥1 backup y su fecha.
    Degrada con gracia si el binario no está (dev) → status 'skipped'.
    El failover completo a sitio DR (Terraform/Ansible) sigue siendo infra-gated.
    """
    try:
        check = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "check"],
            capture_output=True, text=True, timeout=600,
        )
        check_ok = check.returncode == 0

        info = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "--output=json", "info"],
            capture_output=True, text=True, timeout=120,
        )
        backups_count = 0
        latest_backup_epoch = None
        if info.returncode == 0 and info.stdout:
            for stanza in json.loads(info.stdout):
                for b in stanza.get("backup", []):
                    backups_count += 1
                    stop = (b.get("timestamp") or {}).get("stop")
                    if stop and (latest_backup_epoch is None or stop > latest_backup_epoch):
                        latest_backup_epoch = stop

        passed = check_ok and backups_count > 0
        return {
            "status": "passed" if passed else "failed",
            "check_ok": check_ok,
            "backups_count": backups_count,
            "latest_backup_epoch": latest_backup_epoch,
            "check_error": None if check_ok else (check.stderr or "")[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "timeout"}
    except FileNotFoundError:
        logger.warning("pgbackrest not installed — restore-readiness skipped (dev)")
        return {"status": "skipped", "reason": "pgbackrest not installed"}
    except Exception as exc:  # noqa: BLE001
        logger.error("restore-readiness check error: {}", exc)
        return {"status": "failed", "error": str(exc)[:500]}


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
    result = _restore_readiness_check()
    result["test_id"] = test_id
    logger.info("Monthly restore test result: {}", result.get("status"))
    return result


@shared_task(name="backup.run_dr_drill")
def run_dr_drill(drill_id: str | None = None) -> dict:  # pragma: no cover
    """Disaster Recovery drill orchestrator.

    Triggered by ``POST /backup/dr-drills``. The full drill (failover to
    DR site, validation, failback) requires the Hetzner Terraform stack;
    until then this task records the request so the operator can track
    the run via the Operations dashboard.
    """
    logger.info("DR drill triggered (drill_id={})", drill_id)
    # I4: el drill ejecuta la verificación REAL de restaurabilidad del repo
    # (check + info). El failover completo a sitio DR (spin-up servidor efímero,
    # validación, failback) requiere el stack Terraform/Ansible de Hetzner y queda
    # como fase infra documentada: `failover_orchestration`.
    result = _restore_readiness_check()
    result["drill_id"] = drill_id
    result["failover_orchestration"] = "infra_gated_terraform_ansible"
    logger.info("DR drill restore-readiness: {}", result.get("status"))
    return result
