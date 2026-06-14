"""M8 v5.1 — Scheduler nocturno (Celery beat).

Spec §4.2 + §2.13:
- Job nocturno arranca en ventana 22:00-06:00
- Lee verification_runs con scheduled_start <= now() AND status = 'scheduled'
  AND cancel_requested_at IS NULL
- Dispara ejecucion segun categoria

Implementacion:
- Tareas Celery registradas en backend/app/core/celery_app.py
- Scheduler diario que llama a ``dispatch_due_runs`` cada 30 min
  durante la ventana
- Una tarea independiente por run (worker procesa N runs en paralelo)

Si Celery no esta instalado (env de tests sin redis), las funciones
siguen importables y se pueden invocar directamente para tests
unitarios.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.models import VerificationRun


logger = logging.getLogger(__name__)


# Ventana default 22:00-06:00 (override per-contract via M14 · scope_deriver)
DEFAULT_WINDOW_START = time(hour=22, minute=0)
DEFAULT_WINDOW_END = time(hour=6, minute=0)

# Mapping isoweekday -> ScanWindow weekday literal
_WEEKDAY_FROM_ISO = {1: "mon", 2: "tue", 3: "wed", 4: "thu", 5: "fri", 6: "sat", 7: "sun"}


# ════════════════════════════════════════════════════════════════════
# Helpers de ventana
# ════════════════════════════════════════════════════════════════════

def is_in_scan_window(
    now: datetime | None = None,
    *,
    window: dict | None = None,
    window_start: time = DEFAULT_WINDOW_START,
    window_end: time = DEFAULT_WINDOW_END,
) -> bool:
    """¿Es ahora ventana de escaneo?

    Two call modes:
      - **Legacy time-based**: ``is_in_scan_window(now)`` o con
        ``window_start`` / ``window_end`` `time` objects. Window cruza
        medianoche cuando window_start > window_end.
      - **ScanWindow dict** (SAN-B.MB-3.bis.3): ``is_in_scan_window(
        now, window=<dict ScanWindow>)`` aplicando reglas completas
        (tz, dias_ok, dias_bloqueados, fechas_bloqueadas, cross-midnight).

    Si ``window`` está provisto, prevalece sobre window_start/window_end.
    """
    reference = now or datetime.now(timezone.utc)

    if window is not None:
        return _is_in_scan_window_dict(reference, window)

    now_utc = reference.time()
    if window_start < window_end:
        return window_start <= now_utc < window_end
    # Cruza medianoche
    return now_utc >= window_start or now_utc < window_end


def _is_in_scan_window_dict(now: datetime, window: dict) -> bool:
    """Evalúa ScanWindow canónico dict contra datetime now."""
    tz = ZoneInfo(window.get("tz", "Europe/Madrid"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(tz)

    # 1. Fecha bloqueada (festivo cliente etc) → out
    iso_date = local.date().isoformat()
    if iso_date in window.get("fechas_bloqueadas", []):
        return False

    # 2. Día semana bloqueado explícito → out (overrides dias_ok)
    weekday = _WEEKDAY_FROM_ISO[local.isoweekday()]
    if weekday in window.get("dias_bloqueados", []):
        return False

    # 3. Día semana NO permitido → out
    dias_ok = window.get("dias_ok", list(_WEEKDAY_FROM_ISO.values()))
    if weekday not in dias_ok:
        return False

    # 4. Hora dentro del rango (cross-midnight handling)
    start = _parse_hhmm(window["horario_inicio"])
    end = _parse_hhmm(window["horario_fin"])
    current = local.time()
    if start < end:
        return start <= current < end
    # cruza medianoche (ej. 22:00-06:00)
    return current >= start or current < end


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":", 1)
    return time(hour=int(h), minute=int(m))


# ════════════════════════════════════════════════════════════════════
# Dispatch
# ════════════════════════════════════════════════════════════════════

async def list_due_runs(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[VerificationRun]:
    """Devuelve runs con scheduled_start <= now AND status = 'scheduled'
    AND cancel_requested_at IS NULL."""
    cutoff = now or datetime.now(timezone.utc)
    q = await db.execute(
        select(VerificationRun).where(
            VerificationRun.status == "scheduled",
            VerificationRun.scheduled_start.isnot(None),
            VerificationRun.scheduled_start <= cutoff,
            VerificationRun.cancel_requested_at.is_(None),
            VerificationRun.deleted_at.is_(None),
        ).order_by(VerificationRun.scheduled_start.asc())
    )
    return list(q.scalars().all())


async def dispatch_due_runs(
    db: AsyncSession,
    *,
    enforce_window: bool = True,
    now: datetime | None = None,
) -> dict:
    """Recoge runs due y dispara ejecucion para cada uno.

    Si ``enforce_window=True`` y no estamos en ventana, no hace nada.
    Devuelve dict con runs_found / runs_dispatched / runs_skipped_window.
    """
    if enforce_window and not is_in_scan_window(now):
        logger.info(
            "Scheduler M8: fuera de ventana scan_window — skip dispatch."
        )
        return {
            "runs_found": 0,
            "runs_dispatched": 0,
            "runs_skipped_window": 0,
            "reason": "outside_scan_window",
        }

    due = await list_due_runs(db, now=now)
    dispatched = 0
    for run in due:
        try:
            _enqueue_run_execution(run.id)
            dispatched += 1
        except Exception as exc:  # pragma: no cover
            logger.exception("dispatch run=%s fallo: %s", run.id, exc)
    return {
        "runs_found": len(due),
        "runs_dispatched": dispatched,
        "runs_skipped_window": 0,
    }


def _enqueue_run_execution(run_id: uuid.UUID) -> None:
    """Encola la ejecucion del run via Celery (o sincronicamente si
    Celery no disponible).

    Checkpoint 2: registra log; Checkpoint 3 implementa el orquestador
    de fases real (planner que encadena Fase 1 → 2 → 3 segun categoria).
    """
    try:
        from backend.app.core.celery_app import celery_app
        celery_app.send_task(
            "m08_verification.execute_run",
            args=[str(run_id)],
            queue="verification",
        )
        logger.info("Scheduler: encolado run=%s a Celery", run_id)
    except Exception:
        logger.warning(
            "Scheduler: Celery no disponible — run=%s queda como 'scheduled' "
            "hasta que el worker lo recoja.", run_id,
        )


# ════════════════════════════════════════════════════════════════════
# Beat schedule wiring (se registra en core.celery_app)
# ════════════════════════════════════════════════════════════════════

BEAT_SCHEDULE_CONFIG = {
    "m08-dispatch-due-runs": {
        "task": "m08_verification.dispatch_due_runs",
        # Cada 30 minutos durante la ventana (22:00-06:00 UTC).
        # En la practica el cronjob corre cada 30 min todo el dia y la
        # propia tarea revisa is_in_scan_window().
        "schedule": 30 * 60,  # 1800 segundos
    },
}


# Integracion Celery — tareas
try:
    from backend.app.core.celery_app import celery_app

    @celery_app.task(name="m08_verification.dispatch_due_runs")
    def task_dispatch_due_runs() -> dict:
        """Tarea Celery que invoca dispatch_due_runs sincronicamente."""
        import asyncio as _asyncio
        from backend.app.database import async_session

        async def _run():
            async with async_session() as db:
                return await dispatch_due_runs(db)

        try:
            return _asyncio.run(_run())
        except Exception as exc:  # pragma: no cover
            logger.exception("task_dispatch_due_runs fallo: %s", exc)
            return {"error": str(exc)}

    @celery_app.task(name="m08_verification.execute_run")
    def task_execute_run(run_id: str) -> dict:
        """Checkpoint 3 · ejecuta el orquestador autopilot end-to-end.

        Reemplaza el stub: planner por categoría + motores MCP + ZFP 1-5 +
        enrich CVSS/EPSS + ENS/MITRE + triage agéntico + evidencia R6 +
        manifest + coverage (autopilot/orchestrator.orchestrate_run).
        """
        import asyncio as _asyncio
        from backend.app.database import async_session
        from backend.app.motors.m08_verification.autopilot.orchestrator import (
            orchestrate_run,
        )

        async def _run():
            from sqlalchemy import text as _text
            async with async_session() as db:
                # Path de scheduler/Celery: sin request NO hay contexto de tenant.
                # verification_runs/findings tienen FORCE RLS (project_isolation),
                # así que bajo fulkro_app el run sería invisible → ValueError. Es
                # una tarea de sistema que opera sobre un run_id concreto: elevamos
                # a bypassrls (espeja autopilot_api que sí fija contexto).
                await db.execute(_text("SET LOCAL ROLE fulkro_app_bypassrls"))
                summary = await orchestrate_run(db, run_id)
                await db.commit()
                return summary

        try:
            return _asyncio.run(_run())
        except Exception as exc:  # pragma: no cover — fail-closed
            logger.exception("task_execute_run %s falló: %s", run_id, exc)
            return {"run_id": run_id, "status": "failed", "error": str(exc)}
except ImportError:  # pragma: no cover
    pass
