"""Celery tasks for Motor 26 scheduled backup operations.

Persisten su resultado en BD (BackupJob / IntegrityVerification /
BackupRestoreTest / DrDrill) — antes lanzaban el subprocess y devolvían un dict
pero NUNCA tocaban la tabla → los jobs quedaban eternamente 'pending', el
dashboard de salud 'red'/'never' y la evidencia R8/CCN de restore mensual sin
persistir (M10/M11/M12).

Doble vía de invocación:
  - API admin (create_* endpoint) → crea la fila + despacha con su id → la task
    hace start/complete sobre ESA fila.
  - Celery beat (sin args) → la task crea la fila on-the-fly y la completa.

Patrón async-en-task-sync: ``asyncio.run(_coro())`` + ``async_session`` (igual a
m07/m16). Las tablas backup son platform-global (sin tenant) · admin infra →
``SET LOCAL ROLE fulkro_app_bypassrls`` controlado fuera del request.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import text

from backend.app.core.celery_app import celery_app

# Alias compat con patrón original @shared_task
shared_task = celery_app.task


# ════════════════════════════════════════════════════════════════════
# Helpers (sin DB · ejecutan pgbackrest)
# ════════════════════════════════════════════════════════════════════

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


def _parse_latest_backup(info_stdout: str) -> dict:
    """Extrae size + huella del backup más reciente de ``pgbackrest info --json``.

    ``fingerprint`` = sha256 del descriptor del backup que reporta pgBackRest
    (huella verificable de la metadata/manifest summary · NO se afirma que sea el
    hash del dato completo · honest path).
    """
    size_bytes = 0
    fingerprint = ""
    label = ""
    latest_stop = None
    try:
        for stanza in json.loads(info_stdout or "[]"):
            for b in stanza.get("backup", []):
                stop = (b.get("timestamp") or {}).get("stop")
                if stop is not None and (latest_stop is None or stop > latest_stop):
                    latest_stop = stop
                    info = b.get("info") or {}
                    size_bytes = int(
                        info.get("size")
                        or (info.get("repository") or {}).get("size")
                        or 0
                    )
                    label = str(b.get("label") or "")
                    fingerprint = hashlib.sha256(
                        json.dumps(b, sort_keys=True).encode("utf-8")
                    ).hexdigest()
    except (ValueError, TypeError) as exc:
        logger.warning("pgbackrest info parse error: {}", exc)
    return {
        "size_bytes": size_bytes,
        "fingerprint": fingerprint,
        "label": label,
        "stop_epoch": latest_stop,
    }


def _exec_backup(type_flag: str, timeout: int) -> dict:
    """Lanza ``pgbackrest backup`` (full|incr) + info. NO persiste (lo hace el
    wrapper async). status ∈ completed|failed|skipped."""
    try:
        result = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", f"--type={type_flag}", "backup"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            logger.error("pgBackRest {} backup failed: {}", type_flag, result.stderr)
            return {"status": "failed", "error": (result.stderr or "")[:500]}
        info = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "--output=json", "info"],
            capture_output=True, text=True, timeout=120,
        )
        parsed = _parse_latest_backup(info.stdout if info.returncode == 0 else "")
        return {"status": "completed", **parsed}
    except subprocess.TimeoutExpired:
        logger.error("pgBackRest {} backup timed out", type_flag)
        return {"status": "failed", "error": "timeout"}
    except FileNotFoundError:
        logger.warning("pgBackRest not installed — skipping backup (dev mode)")
        return {"status": "skipped", "reason": "pgbackrest not installed"}


# ════════════════════════════════════════════════════════════════════
# Backup jobs (full / incremental) · M10 + M11
# ════════════════════════════════════════════════════════════════════

@shared_task(name="backup.run_pgbackrest_full")
def run_pgbackrest_full(job_id: str | None = None) -> dict:  # pragma: no cover
    """Full PostgreSQL backup via pgBackRest (beat: domingo 02:00)."""
    logger.info("Starting pgBackRest full backup (job_id={})", job_id)
    return asyncio.run(_run_backup("postgres_full", "full", 3600, job_id))


@shared_task(name="backup.run_pgbackrest_incremental")
def run_pgbackrest_incremental(job_id: str | None = None) -> dict:  # pragma: no cover
    """Incremental backup (beat: diario 03:00)."""
    logger.info("Starting pgBackRest incremental backup (job_id={})", job_id)
    return asyncio.run(_run_backup("postgres_incremental", "incr", 1800, job_id))


async def _run_backup(
    backup_type: str, type_flag: str, timeout: int, job_id: str | None,
) -> dict:
    outcome = _exec_backup(type_flag, timeout)
    if outcome["status"] == "skipped":
        return outcome  # dev sin pgbackrest → no se persiste fila engañosa
    from backend.app.database import async_session
    from backend.app.motors.m26_backup.service import BackupService

    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        svc = BackupService(db)
        if job_id:
            jid = uuid.UUID(str(job_id))
            await svc.start_backup(jid)
        else:
            job = await svc.create_backup_job(backup_type)
            await svc.start_backup(job.id)
            jid = job.id
        if outcome["status"] == "completed":
            await svc.complete_backup(
                jid,
                size_bytes=outcome.get("size_bytes", 0),
                hash_sha256=outcome.get("fingerprint", ""),
            )
        else:
            await svc.complete_backup(
                jid, size_bytes=0, hash_sha256="",
                error_message=outcome.get("error", "unknown error"),
            )
        await db.commit()
        outcome["job_id"] = str(jid)
    logger.info(
        "pgBackRest {} → {} (job_id={})",
        backup_type, outcome["status"], outcome.get("job_id"),
    )
    return outcome


# ════════════════════════════════════════════════════════════════════
# Integrity verification · M12
# ════════════════════════════════════════════════════════════════════

@shared_task(name="backup.verify_integrity")
def verify_backup_integrity(check_id: str | None = None) -> dict:  # pragma: no cover
    """Verifica integridad del último backup (beat: tras full semanal)."""
    logger.info("Starting backup integrity verification (check_id={})", check_id)
    return asyncio.run(_run_integrity(check_id))


async def _run_integrity(check_id: str | None) -> dict:
    try:
        result = subprocess.run(
            ["pgbackrest", "--stanza=fulkro", "verify"],
            capture_output=True, text=True, timeout=1800,
        )
    except subprocess.TimeoutExpired:
        outcome = {"status": "failed", "output": "timeout", "discrepancies": 1}
    except FileNotFoundError:
        logger.warning("pgbackrest not installed — integrity skipped (dev)")
        return {"status": "skipped", "reason": "pgbackrest not installed"}
    else:
        passed = result.returncode == 0
        outcome = {
            "status": "passed" if passed else "failed",
            "output": (result.stdout or result.stderr or "")[:1000],
            "discrepancies": 0 if passed else 1,
        }
    from backend.app.database import async_session
    from backend.app.motors.m26_backup.service import BackupService

    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        svc = BackupService(db)
        cid = uuid.UUID(str(check_id)) if check_id else (
            await svc.create_integrity_check("full")
        ).id
        await svc.complete_integrity_check(
            cid,
            discrepancies_found=outcome["discrepancies"],
            report={
                "output": outcome["output"],
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await db.commit()
    outcome["check_id"] = str(cid)
    logger.info("Backup integrity verification: {}", outcome["status"])
    return outcome


# ════════════════════════════════════════════════════════════════════
# Restore test (mensual) · M12
# ════════════════════════════════════════════════════════════════════

@shared_task(name="backup.monthly_restore_test")
def monthly_restore_test(test_id: str | None = None) -> dict:  # pragma: no cover
    """Restore test mensual (beat). Persiste el resultado real del readiness check.

    El failover completo a servidor efímero (Terraform/Ansible) sigue infra-gated;
    el ``validation_report`` lo marca explícitamente (``kind`` = readiness_check).
    """
    logger.info("Monthly restore test triggered (test_id={})", test_id)
    return asyncio.run(_run_restore_test(test_id))


async def _run_restore_test(test_id: str | None) -> dict:
    started = time.monotonic()
    result = _restore_readiness_check()
    rto_seconds = int(time.monotonic() - started)
    if result["status"] == "skipped":
        return result  # dev sin pgbackrest → no se persiste
    from backend.app.database import async_session
    from backend.app.motors.m26_backup.service import BackupService

    passed = result["status"] == "passed"
    validation_report = {
        "all_checks_passed": passed,
        "kind": "restore_readiness_check",  # honest: NO full restore (infra-gated)
        **result,
    }
    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        svc = BackupService(db)
        tid = uuid.UUID(str(test_id)) if test_id else (
            await svc.create_restore_test("monthly_automated")
        ).id
        await svc.complete_restore_test(
            tid, rto_seconds=rto_seconds, validation_report=validation_report,
        )
        await db.commit()
    result["test_id"] = str(tid)
    result["rto_seconds"] = rto_seconds
    logger.info("Monthly restore test result: {}", result.get("status"))
    return result


# ════════════════════════════════════════════════════════════════════
# DR drill (trigger manual admin · trimestral) · M12
# ════════════════════════════════════════════════════════════════════

@shared_task(name="backup.run_dr_drill")
def run_dr_drill(drill_id: str | None = None) -> dict:  # pragma: no cover
    """DR drill. Ejecuta la verificación REAL de restaurabilidad y persiste el
    resultado (RTO = duración del check · RPO = antigüedad del último backup).
    El failover completo a sitio DR sigue infra-gated (Terraform/Ansible)."""
    logger.info("DR drill triggered (drill_id={})", drill_id)
    return asyncio.run(_run_dr_drill(drill_id))


async def _run_dr_drill(drill_id: str | None) -> dict:
    started = time.monotonic()
    result = _restore_readiness_check()
    result["failover_orchestration"] = "infra_gated_terraform_ansible"
    rto_actual = int(time.monotonic() - started)
    if result["status"] == "skipped":
        return result  # dev sin pgbackrest → no se persiste
    # RPO proxy = antigüedad del backup más reciente (ventana de pérdida de datos).
    latest = result.get("latest_backup_epoch")
    now_epoch = datetime.now(timezone.utc).timestamp()
    rpo_actual = int(now_epoch - latest) if latest else 86400
    from backend.app.database import async_session
    from backend.app.motors.m26_backup.service import BackupService

    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        svc = BackupService(db)
        did = uuid.UUID(str(drill_id)) if drill_id else (
            await svc.create_dr_drill()
        ).id
        await svc.complete_dr_drill(
            did,
            rto_actual_seconds=rto_actual,
            rpo_actual_seconds=rpo_actual,
            report_path=f"readiness:{result.get('status')}",
            issues_found=(
                {}
                if result["status"] == "passed"
                else {"check_error": result.get("check_error") or result.get("error")}
            ),
        )
        await db.commit()
    result["drill_id"] = str(did)
    result["rto_actual_seconds"] = rto_actual
    result["rpo_actual_seconds"] = rpo_actual
    logger.info("DR drill restore-readiness: {}", result.get("status"))
    return result
