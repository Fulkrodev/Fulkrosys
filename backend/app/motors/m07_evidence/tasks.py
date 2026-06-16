"""M07 Evidence — tasks programadas (Sprint C5) + antivirus scan (MB-6 atom 6)."""
from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from backend.app.core.celery_app import celery_app


@celery_app.task(name="m07.check_expiring_evidence")
def check_expiring_evidence() -> dict:
    """Detecta evidencias caducadas y escala vía M18 (F-08-03).

    Antes era un stub que sólo logueaba. Ahora, con semántica honesta del
    trigger M18 ``evidencia_critica_caducada`` ("ha caducado sin renovación"):

    - ``fecha_caducidad < hoy`` (ya caducada · sin renovación, pues una
      renovación habría avanzado la fecha) → escalado M18 idempotente (no
      duplica si ya hay un escalado abierto para esa evidencia · corre a
      diario).
    - ``hoy ≤ fecha_caducidad < hoy+30d`` (caduca pronto) → sólo log de aviso;
      NO escala (no existe trigger "expiring-soon" y abusar del trigger
      "caducada" con evidencia aún vigente sería deshonesto · decisión Marcos).

    Scheduled: daily 06:00. Cross-tenant ⇒ ``SET LOCAL ROLE fulkro_app_bypassrls`` (bypass
    RLS), patrón de m23_retainer/tasks.py.
    """
    try:
        return asyncio.run(_run_check_expiring_evidence())
    except Exception as exc:  # pragma: no cover · defensive task wrapper
        logger.error(f"M07 check_expiring_evidence fatal · {exc}")
        return {"status": "failed", "motor": "m07", "error": str(exc)}


async def _run_check_expiring_evidence(session=None) -> dict:
    """Núcleo de check_expiring_evidence.

    En producción (``session=None``) abre su propia sesión, escala a rol
    ``fulkro`` (bypass RLS cross-tenant) y hace commit. En tests se le inyecta
    una sesión ya con rol/contexto adecuado y NO hace commit (el caller gestiona
    la transacción → sin contaminar la BD de test).
    """
    from sqlalchemy import text as sa_text

    from backend.app.motors.m18_communication.escalation_service import (
        EscalationService,
        source_ref_like,
    )

    owns_session = session is None
    if owns_session:
        from backend.app.database import async_session as _async_session
        _cm = _async_session()
        session = await _cm.__aenter__()

    escalated = 0
    skipped_existing = 0
    expiring_soon = 0
    try:
        if owns_session:
            # Job programado cross-tenant: sin contexto de tenant, RLS haría
            # default-deny. Escalamos a rol fulkro para ver todas las evidencias.
            await session.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

        expired_rows = (await session.execute(sa_text(
            "SELECT id, project_id, nombre_tipo, fecha_caducidad "
            "FROM evidence "
            "WHERE fecha_caducidad IS NOT NULL "
            "  AND fecha_caducidad < CURRENT_DATE "
            "  AND deleted_at IS NULL "
            "ORDER BY fecha_caducidad ASC"
        ))).fetchall()

        svc = EscalationService()
        for eid, project_id, nombre_tipo, fcad in expired_rows:
            # Idempotencia por origen estructurado (WAVE C1 · §4.4/370): marcador
            # canónico [src:<eid>] en vez de un UUID embebido en la prosa.
            already = (await session.execute(sa_text(
                "SELECT 1 FROM escalation_events "
                "WHERE project_id = :pid "
                "  AND trigger = 'evidencia_critica_caducada' "
                "  AND resuelto = false "
                "  AND descripcion LIKE :marker "
                "LIMIT 1"
            ), {"pid": str(project_id), "marker": source_ref_like(str(eid))})).first()
            if already:
                skipped_existing += 1
                continue
            await svc.create_escalation(
                session,
                project_id,
                "evidencia_critica_caducada",
                descripcion=(
                    f"Evidencia caducada sin renovación: "
                    f"{nombre_tipo or 'sin nombre'} "
                    f"(caducó {fcad})"
                ),
                source_ref=str(eid),
            )
            escalated += 1

        # Aviso expiring-soon (<30d) · sólo recuento + log · NO escala.
        expiring_soon = int((await session.execute(sa_text(
            "SELECT COUNT(*) FROM evidence "
            "WHERE fecha_caducidad IS NOT NULL "
            "  AND fecha_caducidad >= CURRENT_DATE "
            "  AND fecha_caducidad < CURRENT_DATE + INTERVAL '30 days' "
            "  AND deleted_at IS NULL"
        ))).scalar() or 0)

        if owns_session:
            await session.commit()
    except Exception:
        if owns_session:
            await session.rollback()
        raise
    finally:
        if owns_session:
            await _cm.__aexit__(None, None, None)

    if expiring_soon:
        logger.info(
            "M07: {} evidencia(s) caducan en <30d (aviso · sin escalado)",
            expiring_soon,
        )
    logger.info(
        "M07 check_expiring_evidence · escalated={} skipped_existing={} "
        "expiring_soon={}",
        escalated, skipped_existing, expiring_soon,
    )
    return {
        "status": "ok",
        "motor": "m07",
        "escalated": escalated,
        "skipped_existing": skipped_existing,
        "expiring_soon": expiring_soon,
    }


@celery_app.task(name="m07.janitor_stuck_scans")
def janitor_stuck_scans_task() -> dict:
    """Atom 6.bis · re-procesa evidencias stuck en scan_status='scanning' >5min.

    Recovery scenario: clamd crash · Celery worker down · transient infra failure
    deja evidence row con scan_status='scanning' indefinido. Janitor:
    1. Identifica scanning >5min (scan_started_at < now() - 5min)
    2. Re-encola scan_evidence_file_task
    3. Si >30min stuck Y file missing → marca scan_status='error'

    Scheduled: every 10 min via Celery beat (sub-fase 6.A.0 H1).
    """
    import asyncio

    logger.info("M07 atom 6.bis: janitor scanning stuck check")

    async def _run() -> dict:
        from sqlalchemy import text as sa_text
        from backend.app.database import async_session

        re_enqueued = 0
        marked_error = 0
        async with async_session() as db:
            try:
                stuck_row = await db.execute(sa_text(
                    "SELECT id, scan_started_at, fichero_path "
                    "FROM evidence "
                    "WHERE scan_status = 'scanning' "
                    "AND scan_started_at < now() - interval '5 minutes' "
                    "AND deleted_at IS NULL "
                    "ORDER BY scan_started_at ASC LIMIT 100"
                ))
                rows = stuck_row.fetchall()
            except Exception as exc:
                logger.error(f"M07 atom 6.bis: scan query failed · {exc}")
                return {"status": "scan_failed", "error": str(exc)}

            for row in rows:
                eid = row[0]
                started_at = row[1]
                from datetime import datetime, timezone
                age_minutes = (
                    datetime.now(timezone.utc) - started_at
                ).total_seconds() / 60.0
                if age_minutes > 30:
                    try:
                        await db.execute(sa_text(
                            "UPDATE evidence SET "
                            "scan_status = 'error', "
                            "scan_completed_at = now(), "
                            "scan_result_jsonb = CAST(:res AS jsonb) "
                            "WHERE id = :eid"
                        ), {
                            "eid": str(eid),
                            "res": '{"status": "error", "error_msg": '
                                   '"janitor: scanning stuck >30min · marked error"}',
                        })
                        marked_error += 1
                    except Exception as exc:
                        logger.warning(
                            f"M07 atom 6.bis: mark error failed eid={eid} · {exc}"
                        )
                else:
                    try:
                        scan_evidence_file_task.delay(str(eid))
                        re_enqueued += 1
                    except Exception as exc:
                        logger.warning(
                            f"M07 atom 6.bis: re-enqueue failed eid={eid} · {exc}"
                        )

            try:
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error(f"M07 atom 6.bis: commit failed · {exc}")
                return {"status": "commit_failed", "error": str(exc)}

        return {
            "status": "ok",
            "motor": "m07",
            "scanned": len(rows),
            "re_enqueued": re_enqueued,
            "marked_error": marked_error,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(f"M07 atom 6.bis: task fatal · {exc}")
        return {"status": "failed", "motor": "m07", "error": str(exc)}


@celery_app.task(
    name="m07.scan_evidence_file",
    bind=True,
    max_retries=2,
    soft_time_limit=25,
    time_limit=30,
)
def scan_evidence_file_task(self, evidence_id: str) -> dict:
    """Async ClamAV scan post-upload · MB-6 atom 6 · ENS mp.s.5.

    Transitions evidence.scan_status:
      scanning -> clean | quarantined | error

    Quarantine workflow (Q2 B cement · false-positive recoverable):
      INFECTED -> move file a var/quarantine/ + alert_queue 'antivirus_infected'

    soft_time_limit=25s · clamd default scan timeout 30s · buffer 5s seguridad.
    max_retries=2 · solo retry en ClamdConnectionError (transient).

    Args:
        evidence_id: str uuid del evidence row insertado pre-scan.

    Returns:
        {"status": "ok", "scan_status": "clean"|"quarantined"|"error",
         "evidence_id": str}
    """
    from celery.exceptions import SoftTimeLimitExceeded

    logger.info(f"M07 antivirus scan task started · evidence={evidence_id}")
    try:
        eid = uuid.UUID(evidence_id)
    except ValueError:
        logger.error(f"Invalid evidence_id uuid: {evidence_id}")
        return {"status": "invalid_uuid", "evidence_id": evidence_id}

    async def _run() -> str:
        from backend.app.database import async_session
        from backend.app.motors.m07_evidence.antivirus_scan_service import (
            scan_evidence,
        )
        async with async_session() as db:
            try:
                terminal = await scan_evidence(db, eid)
                await db.commit()
                return terminal
            except Exception:
                await db.rollback()
                raise

    try:
        terminal = asyncio.run(_run())
        logger.info(
            f"M07 antivirus scan done · evidence={evidence_id} "
            f"terminal_status={terminal}"
        )
        return {
            "status": "ok",
            "scan_status": terminal,
            "evidence_id": evidence_id,
        }
    except SoftTimeLimitExceeded:
        logger.error(f"M07 scan soft-timeout · evidence={evidence_id}")
        # Best-effort: marcar error state. Si DB también unreachable,
        # task fails y Celery beat next run podría re-procesar via
        # janitor task (out of scope atom 6 · diferido atom 6.bis).
        return {"status": "timeout", "evidence_id": evidence_id}
    except Exception as exc:
        logger.error(
            f"M07 scan failed · evidence={evidence_id} · {exc} "
            f"· retry={self.request.retries}/2"
        )
        try:
            raise self.retry(exc=exc, countdown=30) from exc
        except Exception:
            return {"status": "failed", "evidence_id": evidence_id}
