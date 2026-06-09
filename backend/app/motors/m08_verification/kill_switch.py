"""M8 v5.1 — Kill switch real.

Spec §2.13:
- Marcos pulsa kill → backend marca ``cancel_requested_at = now()``
- Watcher (KillWatcher) chequea cada 1s los runs cancellable
- Si encuentra cancel_requested_at != NULL → SIGTERM al process group
  del subprocess hijo (ej. nuclei) → wait 3s → SIGKILL
- ``cancel_completed_at = now()`` cuando todo terminado
- Garantia: tiempo desde request hasta cancellable < 5s

Implementacion:

- ``request_kill(db, run_id)`` marca BD (esta funcion ya existia en
  Checkpoint 1; ahora la enriquecemos).
- ``register_subprocess(run_id, pgid)`` registra el process group
  asociado a un run para que el watcher pueda matarlo.
- ``KillWatcher`` (background asyncio task) recorre los procesos
  registrados y, si su run tiene cancel_requested_at, los mata.

Tests verifican que el watcher mata un sleep largo en <5s.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.motors.m08_verification.models import VerificationRun
from backend.app.motors.m08_verification.service import (
    RunStateError,
    VerificationService,
)


logger = logging.getLogger(__name__)


CANCELLABLE_STATES = {
    "pending", "authorized", "scheduled",
    "phase1_running", "phase2_running", "phase3_validating",
}


# ════════════════════════════════════════════════════════════════════
# Registro in-memory de subprocess hijos por run
# ════════════════════════════════════════════════════════════════════

@dataclass
class _RunSubprocessRegistry:
    """Mapping run_id → set[pgid]. In-memory porque solo importa al
    proceso que lanzo el subprocess."""
    by_run: dict[str, set[int]] = field(default_factory=dict)

    def register(self, run_id: uuid.UUID, pgid: int) -> None:
        self.by_run.setdefault(str(run_id), set()).add(pgid)

    def unregister(self, run_id: uuid.UUID, pgid: int) -> None:
        self.by_run.get(str(run_id), set()).discard(pgid)

    def pgids_for(self, run_id: uuid.UUID) -> set[int]:
        return set(self.by_run.get(str(run_id), set()))

    def all_runs(self) -> list[str]:
        return list(self.by_run.keys())


_REGISTRY = _RunSubprocessRegistry()


def register_subprocess(run_id: uuid.UUID, pgid: int) -> None:
    """Registra un process group (pgid) asociado a un run."""
    _REGISTRY.register(run_id, pgid)


def unregister_subprocess(run_id: uuid.UUID, pgid: int) -> None:
    _REGISTRY.unregister(run_id, pgid)


@contextmanager
def tracked_subprocess(run_id: uuid.UUID, pid: int):
    """Context manager: registra pgid del pid mientras este vivo.

    El runner usa esto despues de ``asyncio.create_subprocess_exec``:

        with tracked_subprocess(run_id, proc.pid):
            await proc.communicate()
    """
    try:
        pgid = os.getpgid(pid)
    except (ProcessLookupError, OSError):
        pgid = pid
    register_subprocess(run_id, pgid)
    try:
        yield pgid
    finally:
        unregister_subprocess(run_id, pgid)


# ════════════════════════════════════════════════════════════════════
# Request kill (REST API entry point)
# ════════════════════════════════════════════════════════════════════

async def request_kill(
    db: AsyncSession,
    run_id: uuid.UUID,
    requested_by: str = "marcos",
) -> VerificationRun:
    """Marca el run como cancel_requested. El watcher lo detectara
    en su proximo tick (max 1s) y matara los process groups."""
    svc = VerificationService(db)
    run = await svc.get_run(run_id)
    if run.status not in CANCELLABLE_STATES and run.status != "cancelled":
        raise RunStateError(
            f"No se puede cancelar run en estado '{run.status}'."
        )
    if run.cancel_requested_at is not None:
        # Ya solicitado; idempotente
        return run
    run.cancel_requested_at = datetime.now(timezone.utc)
    run.cancel_requested_by = requested_by
    if run.status != "cancelled":
        run.status = "cancelled"
    await db.flush()

    # Inmediatamente tambien intentamos matar los pgids registrados
    # (bypass watcher: mas rapido). El watcher actua como respaldo.
    kill_run_processes_now(run_id)
    return run


def kill_run_processes_now(run_id: uuid.UUID) -> int:
    """Mata sincronamente todos los pgids registrados para un run.

    Devuelve cuantos pgids se intentaron matar.
    """
    pgids = _REGISTRY.pgids_for(run_id)
    n = 0
    for pgid in pgids:
        try:
            os.killpg(pgid, signal.SIGTERM)
            n += 1
        except ProcessLookupError:
            # Ya no existe — limpieza
            unregister_subprocess(run_id, pgid)
            continue
        except OSError as exc:
            logger.warning("kill_run_processes: SIGTERM pgid=%s fallo: %s", pgid, exc)
    return n


def force_kill_run_processes(run_id: uuid.UUID) -> int:
    """SIGKILL — usar tras grace period 3s si SIGTERM no funciono."""
    pgids = _REGISTRY.pgids_for(run_id)
    n = 0
    for pgid in pgids:
        try:
            os.killpg(pgid, signal.SIGKILL)
            n += 1
        except (ProcessLookupError, OSError):
            unregister_subprocess(run_id, pgid)
    return n


# ════════════════════════════════════════════════════════════════════
# KillWatcher (background asyncio task)
# ════════════════════════════════════════════════════════════════════

class KillWatcher:
    """Background watcher que cada tick (default 1s):
    - Lee runs con cancel_requested_at IS NOT NULL AND cancel_completed_at IS NULL
    - Para cada uno, manda SIGTERM al process group, espera 3s, manda SIGKILL.
    - Marca cancel_completed_at = now() cuando termina.

    Diseno simplificado: el watcher es de un solo proceso (el que lanzo
    los subprocess). En produccion multi-worker, el bypass sincronico
    de ``kill_run_processes_now`` desde ``request_kill`` cubre el 99%
    de los casos. El watcher es respaldo.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        tick_seconds: float = 1.0,
        sigkill_grace_seconds: float = 3.0,
    ) -> None:
        self.session_factory = session_factory
        self.tick_seconds = tick_seconds
        self.sigkill_grace_seconds = sigkill_grace_seconds
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="m8v51-kill-watcher")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception as exc:  # pragma: no cover
                logger.exception("KillWatcher tick fallo: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.tick_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def _tick(self) -> None:
        async with self.session_factory() as db:
            pending_q = await db.execute(
                select(VerificationRun).where(
                    VerificationRun.cancel_requested_at.isnot(None),
                    VerificationRun.cancel_completed_at.is_(None),
                )
            )
            for run in pending_q.scalars().all():
                await self._handle_cancellation(db, run)

    async def _handle_cancellation(
        self, db: AsyncSession, run: VerificationRun,
    ) -> None:
        # 1. SIGTERM
        n_term = kill_run_processes_now(run.id)
        # 2. Grace period
        await asyncio.sleep(self.sigkill_grace_seconds)
        # 3. SIGKILL
        n_kill = force_kill_run_processes(run.id)
        # 4. Marcar completado
        await db.execute(
            update(VerificationRun)
            .where(VerificationRun.id == run.id)
            .values(cancel_completed_at=datetime.now(timezone.utc))
        )
        await db.flush()
        logger.info(
            "KillWatcher: run=%s SIGTERM→%d SIGKILL→%d completed",
            run.id, n_term, n_kill,
        )


# ════════════════════════════════════════════════════════════════════
# Helper para mock-test (sin BD): mata por pgid directo
# ════════════════════════════════════════════════════════════════════

async def watch_and_kill_until(
    run_id: uuid.UUID,
    *,
    cancellation_check,    # async callable → bool ('hay cancel?')
    tick_seconds: float = 0.5,
    sigkill_grace_seconds: float = 3.0,
    deadline_seconds: float = 5.0,
) -> tuple[bool, float]:
    """Helper para tests: mata el run cuando cancellation_check() vuelve True.

    Devuelve (was_killed, elapsed_seconds).
    """
    start = time.monotonic()
    while time.monotonic() - start < deadline_seconds:
        if await cancellation_check():
            kill_run_processes_now(run_id)
            await asyncio.sleep(min(sigkill_grace_seconds, 1.0))
            force_kill_run_processes(run_id)
            return True, time.monotonic() - start
        await asyncio.sleep(tick_seconds)
    return False, time.monotonic() - start
