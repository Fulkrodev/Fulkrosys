"""SQLAlchemy event listeners → SSE dispatch (MB-13.3 · ADR-035).

Modelos vigilados con ``project_id`` directo (audit empírico SAN-D):
- ``backend.app.models.ens.DdaEntry``               (M03 DdA)
- ``backend.app.models.documents.Evidence``         (M07 evidence)
- ``backend.app.models.core.Project``               (fase column)

Cambio en {DdaEntry · Evidence} dispatch ``readiness_changed`` para
invalidar query dashboard / readiness UI cliente.

Cambio en ``Project.fase`` dispatch ``phase_changed`` con old/new phase.

Modelos NO vigilados (con justificación):
- ``Asset`` (risk.py): no tiene project_id directo (vía system_id →
  Systems join). Future: listener via session.merge events si se
  necesita resolución asíncrona del project.
- ``MageritThreat`` (m02_magerit/models.py): es catálogo global
  (no per-project) · cambios en catálogo NO afectan readiness
  per-project · listener no aplica.

Robustez: si el commit ocurre fuera de un event loop activo
(p.ej. tests sync DB pre-asyncio o background workers), el listener
captura excepción ``RuntimeError`` y registra warning sin abortar la
transacción DB (LECCIÓN-OPS-004 + design seguro).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, object_session

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.models.core import Project
from backend.app.models.documents import Evidence
from backend.app.models.ens import DdaEntry

logger = logging.getLogger(__name__)


def _safe_fire(coro) -> None:
    """Lanza coroutine en el event loop activo · skip si no hay loop.

    SQLAlchemy hooks ``after_*`` son síncronos. ``asyncio.create_task``
    requiere event loop running. En FastAPI runtime (uvicorn) siempre
    lo hay. En tests sync (DB session sin asyncio.run wrapper) no hay
    loop · loggea debug y descarta coroutine para no leak.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        coro.close()
        logger.debug(
            "SSE dispatch skipped · no running event loop (sync caller)",
        )
        return
    loop.create_task(coro)


def _project_id_of(target: Any) -> UUID | None:
    pid = getattr(target, "project_id", None)
    if isinstance(pid, UUID):
        return pid
    if isinstance(pid, str):
        try:
            return UUID(pid)
        except ValueError:
            return None
    return None


_PENDING_KEY = "_sse_pending_events"


def _queue(target: Any, event_type: str, data: dict) -> None:
    """Encola el evento SSE en la sesión · se emite SOLO en after_commit.

    Antes se hacía _safe_fire directo en after_insert/update (pre-commit · nivel
    flush) → si la transacción hacía ROLLBACK, el portal ya había recibido un
    evento FANTASMA de un cambio que nunca se persistió (auditoría 2026-06-07).
    Ahora se acumula y se emite tras el commit (o se descarta en rollback).
    """
    session = object_session(target)
    if session is None:
        # Sin sesión asociada (caso raro) · best-effort inmediato (comportamiento previo)
        _safe_fire(
            sse_dispatcher.dispatch(
                channel=f"project:{data['project_id']}",
                event_type=event_type,
                data=data,
            ),
        )
        return
    session.info.setdefault(_PENDING_KEY, []).append((event_type, data))


def _trigger_readiness(target: Any, model_name: str) -> None:
    project_id = _project_id_of(target)
    if project_id is None:
        return
    _queue(
        target,
        "readiness_changed",
        {"project_id": str(project_id), "trigger_model": model_name},
    )


def _on_dda_entry_change(
    _mapper, _connection, target: DdaEntry,
) -> None:
    _trigger_readiness(target, "DdaEntry")


def _on_evidence_change(
    _mapper, _connection, target: Evidence,
) -> None:
    _trigger_readiness(target, "Evidence")


def _on_project_update(
    _mapper, _connection, target: Project,
) -> None:
    """Si cambia ``Project.fase`` encola ``phase_changed`` (emitido en commit)."""
    state = inspect(target)
    fase_history = state.attrs.fase.history
    if not fase_history.has_changes():
        return
    old_phase = fase_history.deleted[0] if fase_history.deleted else None
    new_phase = fase_history.added[0] if fase_history.added else None
    if old_phase == new_phase:
        return

    _queue(
        target,
        "phase_changed",
        {
            "project_id": str(target.id),
            "old_phase": old_phase,
            "new_phase": new_phase,
        },
    )


def _on_session_commit(session: Session) -> None:
    """Emite los eventos SSE encolados · SOLO cuando la transacción committeó."""
    pending = session.info.pop(_PENDING_KEY, None)
    if not pending:
        return
    for event_type, data in pending:
        _safe_fire(
            sse_dispatcher.dispatch(
                channel=f"project:{data['project_id']}",
                event_type=event_type,
                data=data,
            ),
        )


def _on_session_rollback(session: Session) -> None:
    """Descarta los eventos encolados si hubo ROLLBACK (evita evento fantasma)."""
    session.info.pop(_PENDING_KEY, None)


_LISTENERS_REGISTERED = False


def register_listeners() -> None:
    """Registra los listeners SQLAlchemy. Idempotente."""
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return
    _LISTENERS_REGISTERED = True

    event.listen(DdaEntry, "after_insert", _on_dda_entry_change)
    event.listen(DdaEntry, "after_update", _on_dda_entry_change)

    event.listen(Evidence, "after_insert", _on_evidence_change)
    event.listen(Evidence, "after_update", _on_evidence_change)

    event.listen(Project, "after_update", _on_project_update)

    # Emisión diferida a commit (anti evento fantasma · auditoría 2026-06-07)
    event.listen(Session, "after_commit", _on_session_commit)
    event.listen(Session, "after_rollback", _on_session_rollback)

    logger.info(
        "SSE event listeners registered (DdaEntry · Evidence · Project.fase · "
        "after_commit deferred dispatch · anti-phantom)",
    )


register_listeners()
