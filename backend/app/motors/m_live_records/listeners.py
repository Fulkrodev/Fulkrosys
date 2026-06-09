"""SQLAlchemy event listeners · sub-atom 1.C.B fase 3c.

Pattern non-invasive (idéntico a ``pentest_auto_trigger_events.py``):
``after_insert`` listeners en Incident · Change · ProviderAssessment
capturan los campos relevantes y disparan ``_safe_fire`` con el helper async
correspondiente que abre una sesión nueva (post-parent-commit semantics).

Registro idempotente via ``_LISTENERS_REGISTERED`` flag para evitar duplicar
si el módulo se re-importa (tests · reloader uvicorn dev).
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import event

from backend.app.models.live_record import LiveRecord  # noqa: F401  ensure metadata
from backend.app.models.m14_providers import ProviderAssessment
from backend.app.models.operations import Change, Incident
from backend.app.motors.m_live_records.auto_population import (
    auto_populate_change_to_e308,
    auto_populate_incident_to_e305,
    auto_populate_provider_assessment_to_e312,
)

logger = logging.getLogger(__name__)

_LISTENERS_REGISTERED = False


def _safe_fire(coro) -> None:
    """Schedule a coroutine in the running event loop · drop if no loop.

    Mismo pattern que ``pentest_auto_trigger_events._safe_fire``. Si no hay
    loop (sync caller · ej. seeds, tests sync), cierra el coroutine en silencio.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        coro.close()
        return
    loop.create_task(coro)


def _on_incident_inserted(_mapper, _connection, target: Incident) -> None:
    """M19 Incident after_insert → E-305 entry (post-commit)."""
    try:
        _safe_fire(
            auto_populate_incident_to_e305(
                project_id=target.project_id,
                incident_id=target.id,
                severidad=target.severidad,
                descripcion=target.descripcion,
                fecha=target.fecha,
                created_by=None,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("incident after_insert listener failed: %s", exc)


def _on_change_inserted(_mapper, _connection, target: Change) -> None:
    """M28 Change after_insert → E-308 entry (post-commit)."""
    try:
        _safe_fire(
            auto_populate_change_to_e308(
                project_id=target.project_id,
                change_id=target.id,
                descripcion=target.descripcion,
                solicitante=target.solicitante,
                fecha=target.created_at,
                created_by=None,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("change after_insert listener failed: %s", exc)


def _on_provider_assessment_inserted(
    _mapper, _connection, target: ProviderAssessment
) -> None:
    """M14 ProviderAssessment after_insert → E-312 entry (post-commit)."""
    try:
        _safe_fire(
            auto_populate_provider_assessment_to_e312(
                project_id=target.project_id,
                assessment_id=target.id,
                provider_id=target.provider_id,
                assessment_date=target.assessment_date,
                assessor=target.assessor,
                risk_score=target.risk_score,
                risk_level=target.risk_level,
                decision=target.decision,
                created_by=None,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "provider_assessment after_insert listener failed: %s", exc
        )


def register_listeners() -> None:
    """Register the 3 after_insert listeners idempotently."""
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return

    event.listen(Incident, "after_insert", _on_incident_inserted)
    event.listen(Change, "after_insert", _on_change_inserted)
    event.listen(
        ProviderAssessment, "after_insert", _on_provider_assessment_inserted
    )

    _LISTENERS_REGISTERED = True
    logger.info(
        "live_records: registered 3 after_insert listeners "
        "(Incident → E-305 · Change → E-308 · ProviderAssessment → E-312)"
    )


def unregister_listeners() -> None:
    """Remove listeners (use in tests that want to disable auto-population)."""
    global _LISTENERS_REGISTERED
    if not _LISTENERS_REGISTERED:
        return
    try:
        event.remove(Incident, "after_insert", _on_incident_inserted)
        event.remove(Change, "after_insert", _on_change_inserted)
        event.remove(
            ProviderAssessment, "after_insert",
            _on_provider_assessment_inserted,
        )
    finally:
        _LISTENERS_REGISTERED = False
