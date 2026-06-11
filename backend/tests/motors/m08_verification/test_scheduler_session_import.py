"""Regresión: las tareas Celery del autopilot M8 deben importar el factory de
sesión REAL (`async_session`), no un nombre inexistente.

Bug histórico (2026-06-11): `scheduler.py` importaba `async_session_factory`
DENTRO de `task_dispatch_due_runs` / `task_execute_run`. Ese símbolo no existe
en `backend.app.database` (el factory es `async_session`), así que cada dispatch
del autopilot reventaba con ImportError en runtime → el pentest autónomo NUNCA
corría end-to-end. La suite no lo cazaba porque los tests llaman a
`orchestrate_run` directamente, saltándose los wrappers Celery (que solo invoca
Celery en producción). Este test cierra ese hueco con un check estático barato.
"""
from __future__ import annotations

import inspect


def test_database_exposes_async_session_factory():
    import backend.app.database as db

    assert hasattr(db, "async_session"), (
        "backend.app.database debe exponer `async_session` (el factory real)"
    )


def test_scheduler_does_not_reference_nonexistent_factory():
    import backend.app.motors.m08_verification.scheduler as scheduler

    src = inspect.getsource(scheduler)
    assert "async_session_factory" not in src, (
        "scheduler.py referencia `async_session_factory`, que NO existe en "
        "backend.app.database → las tareas Celery del autopilot reventarían en "
        "runtime. Usar `async_session`."
    )
    assert "from backend.app.database import async_session" in src, (
        "las tareas Celery deben importar `async_session` de backend.app.database"
    )
