"""Tests · Cross-actor blocking semantics (1.D.G v3.11 sub-atom B).

Cubre:
- event_matches_audience filtering per audience (cliente vs admin)
- ADMIN_EVENT_TYPES vs CLIENTE_EVENT_TYPES sets
- Cliente recibe step_completed solo si primary_actor == "admin" (Marcos terminó)
- Cliente recibe step_unblocked solo si primary_actor == "cliente" (su turno)
- Admin recibe TODOS los eventos
- ClientTaskService transition guard prereqs enforce in_progress
"""
from __future__ import annotations

import pytest

from backend.app.core.sse_dispatcher import (
    ADMIN_EVENT_TYPES,
    CLIENTE_EVENT_TYPES,
    event_matches_audience,
)


# ============= ADMIN_EVENT_TYPES + CLIENTE_EVENT_TYPES sets =============


def test_admin_event_types_includes_step_events():
    assert "step_completed" in ADMIN_EVENT_TYPES
    assert "step_unblocked" in ADMIN_EVENT_TYPES
    assert "step_blocked" in ADMIN_EVENT_TYPES


def test_admin_event_types_includes_legacy_events():
    """Backward-compat MB-13.3 events."""
    assert "readiness_changed" in ADMIN_EVENT_TYPES
    assert "phase_changed" in ADMIN_EVENT_TYPES
    assert "alert_new" in ADMIN_EVENT_TYPES


def test_cliente_admin_event_audiences_are_distinct_by_design():
    """Las audiencias admin y cliente son DISTINTAS, no subset.

    Diseño de audiencias real (sse_dispatcher · filosofía cliente-mínimo):
    admin y cliente comparten SOLO los eventos cross-actor (workflow steps +
    chat); el resto de eventos cliente-facing (client_notification, m01/m02
    sync, cloud_remediation lifecycle, signing, plan, accompaniment, pentest)
    son EXCLUSIVOS de cliente y NO se eco-difunden a admin. El antiguo invariante
    CLIENTE ⊆ ADMIN era incorrecto by design (Marcos 2026-05-31: admin no recibe
    el eco de eventos puramente de cliente). Fuente: diseño de audiencias
    event_matches_audience en backend/app/core/sse_dispatcher.py.

    NOTA Ola 3 #14 (2026-06-04): phase_changed pasa a COMPARTIDO (admin+cliente)
    por política de transparencia al cliente · el test sigue verde (sigue sin ser
    subset), solo que lo compartido ya no es "cross-actor steps + chat" en exclusiva.
    """
    shared = CLIENTE_EVENT_TYPES & ADMIN_EVENT_TYPES
    # Comparten los eventos cross-actor (workflow steps + chat)
    assert "step_completed" in shared
    assert "chat_message_new" in shared
    # Pero cliente tiene eventos propios que NO se eco-difunden a admin
    cliente_only = CLIENTE_EVENT_TYPES - ADMIN_EVENT_TYPES
    assert cliente_only, "cliente debe tener eventos cliente-facing exclusivos"
    assert "client_notification.created" in cliente_only
    assert "m02.magerit.updated" in cliente_only


def test_cliente_event_types_excludes_admin_internal_events():
    """Cliente NO recibe readiness_changed/alert_new · admin-internos.

    Ola 3 #14 (2026-06-04): phase_changed YA NO está excluido · ahora es
    cliente-facing (política de transparencia de progreso · ver
    test_audience_cliente_receives_phase_changed). readiness_changed y
    alert_new SIGUEN admin-internos.
    """
    assert "readiness_changed" not in CLIENTE_EVENT_TYPES
    assert "alert_new" not in CLIENTE_EVENT_TYPES
    assert "phase_changed" in CLIENTE_EVENT_TYPES  # política nueva #14


# ============= event_matches_audience =============


def test_audience_admin_passes_all_admin_events():
    for ev in ADMIN_EVENT_TYPES:
        assert event_matches_audience(ev, "admin", {}) is True


def test_audience_admin_blocks_unknown_event():
    assert event_matches_audience("unknown_event", "admin", {}) is False


def test_audience_admin_receives_signing_signed():
    """Ola 3 #12 · el admin VE la firma del cliente en realtime (motor de avance).
    Son siempre acciones del cliente → membresía basta, sin filtro cross-actor."""
    assert event_matches_audience("signing.signed", "admin", {}) is True


def test_audience_admin_receives_signing_declined():
    assert event_matches_audience("signing.declined", "admin", {}) is True


def test_admin_event_types_includes_signing_signed_declined():
    """Ola 3 #12 · signing.signed/.declined en ADMIN. signing.requested NO
    (lo origina el propio admin · eco inútil)."""
    assert "signing.signed" in ADMIN_EVENT_TYPES
    assert "signing.declined" in ADMIN_EVENT_TYPES
    assert "signing.requested" not in ADMIN_EVENT_TYPES


def test_audience_cliente_blocks_readiness_changed():
    """Cliente NO debe recibir readiness_changed · admin-internal."""
    assert event_matches_audience(
        "readiness_changed", "cliente", {"primary_actor": "cliente"},
    ) is False


def test_audience_cliente_receives_phase_changed():
    """Ola 3 #14 · POLÍTICA NUEVA (2026-06-04): el cliente VE su progreso de
    fase en realtime (transparencia outcome-as-a-service). Antes bloqueado
    como admin-interno; revertido deliberadamente."""
    assert event_matches_audience(
        "phase_changed", "cliente", {"primary_actor": "cliente"},
    ) is True


def test_audience_cliente_blocks_alert_new():
    assert event_matches_audience(
        "alert_new", "cliente", {"primary_actor": "cliente"},
    ) is False


def test_audience_cliente_receives_step_completed_admin_actor():
    """Cliente recibe step_completed si Marcos (admin) terminó algo."""
    assert event_matches_audience(
        "step_completed", "cliente", {"primary_actor": "admin"},
    ) is True


def test_audience_cliente_does_not_receive_step_completed_self_actor():
    """Cliente NO debe recibir spam own step_completed events."""
    assert event_matches_audience(
        "step_completed", "cliente", {"primary_actor": "cliente"},
    ) is False


def test_audience_cliente_receives_step_unblocked_for_cliente():
    """Cliente recibe step_unblocked si LE TOCA actuar."""
    assert event_matches_audience(
        "step_unblocked", "cliente", {"primary_actor": "cliente"},
    ) is True


def test_audience_cliente_does_not_receive_step_unblocked_for_admin():
    """Cliente NO debe ver eventos que LE TOCA a Marcos."""
    assert event_matches_audience(
        "step_unblocked", "cliente", {"primary_actor": "admin"},
    ) is False


def test_audience_cliente_step_blocked_only_cliente_actor():
    """step_blocked sólo si bloquea acción cliente."""
    assert event_matches_audience(
        "step_blocked", "cliente", {"primary_actor": "cliente"},
    ) is True
    assert event_matches_audience(
        "step_blocked", "cliente", {"primary_actor": "admin"},
    ) is False


def test_audience_unknown_returns_false():
    """Audience unknown · safe default deny."""
    assert event_matches_audience(
        "step_completed", "guest", {"primary_actor": "admin"},
    ) is False


# ============= ClientTaskService transition guard prereqs =============


@pytest.mark.asyncio
async def test_transition_guard_blocks_in_progress_when_prereq_missing(monkeypatch):
    """transition("in_progress") raises TaskError si prereqs no done."""
    # Test exercita el guard · skip-gate env var must be unset
    monkeypatch.delenv("FULKRO_SKIP_WORKFLOW_GATES", raising=False)
    import uuid
    from types import SimpleNamespace
    from backend.app.motors.m21_portal_cliente.task_service import (
        ClientTaskService, TaskError,
    )
    from backend.app.motors.m21_portal_cliente.task_templates_loader import TaskTemplate

    task_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # Fake task X · template requires prereq A
    task = SimpleNamespace(
        id=task_id,
        project_id=project_id,
        template_id="X",
        phase="diagnostico",
        title="X step",
        description=None,
        status="pending",
        started_at=None,
        completed_at=None,
        blocked_reason=None,
        priority=0,
    )

    tmpl_x = TaskTemplate(
        id="X", phase="diagnostico",
        applicable_categories="ALL", applicable_archetypes="ALL",
        title="X step",
        prerequisite_template_ids=["A"],
    )
    tmpl_a = TaskTemplate(
        id="A", phase="diagnostico",
        applicable_categories="ALL", applicable_archetypes="ALL",
        title="A prereq",
    )

    # Mock db.get to return task
    class FakeDb:
        async def get(self, model, _id):
            return task

        async def execute(self, _query):
            class _Res:
                def scalars(self):
                    class _Sc:
                        def all(self):
                            return []  # no tasks · A missing
                    return _Sc()
            return _Res()

        async def flush(self):
            pass

    monkeypatch.setattr(
        "backend.app.motors.m21_portal_cliente.task_service.get_template_by_id",
        lambda tid: {"X": tmpl_x, "A": tmpl_a}.get(tid),
    )

    svc = ClientTaskService(FakeDb())
    with pytest.raises(TaskError) as exc:
        await svc.transition(task_id, "in_progress")
    assert "bloqueado" in str(exc.value).lower() or "prerequisit" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_transition_guard_bypass_with_enforce_false(monkeypatch):
    """enforce_prereqs=False permite transition aunque prereqs missing."""
    import uuid
    from types import SimpleNamespace
    from backend.app.motors.m21_portal_cliente.task_service import ClientTaskService
    from backend.app.motors.m21_portal_cliente.task_templates_loader import TaskTemplate

    task_id = uuid.uuid4()
    task = SimpleNamespace(
        id=task_id,
        project_id=uuid.uuid4(),
        template_id="X",
        status="pending",
        started_at=None,
        completed_at=None,
        blocked_reason=None,
    )

    tmpl_x = TaskTemplate(
        id="X", phase="diagnostico",
        applicable_categories="ALL", applicable_archetypes="ALL",
        title="X step",
        prerequisite_template_ids=["A"],
    )

    class FakeDb:
        async def get(self, model, _id):
            return task

        async def execute(self, _query):
            return type("R", (), {
                "scalars": lambda s: type("S", (), {"all": lambda x: []})()
            })()

        async def flush(self):
            pass

    monkeypatch.setattr(
        "backend.app.motors.m21_portal_cliente.task_service.get_template_by_id",
        lambda tid: tmpl_x if tid == "X" else None,
    )

    svc = ClientTaskService(FakeDb())
    # Should NOT raise · enforce_prereqs=False bypass
    result = await svc.transition(task_id, "in_progress", enforce_prereqs=False)
    assert result.status == "in_progress"
