"""Tests · DependencyResolver state machine (1.D.G v3.11 sub-atom B).

Cubre:
- derive_primary_actor heuristica (admin · cliente · system)
- check_dependencies_satisfied con prereqs done/not_done/missing
- resolve_step_status estados blocked · available · in_progress · done
- blocker_reason format friendly per actor
- backward-compat "completed" vs "done" terminal status
- TaskTemplate primary_actor explícito override sostiene
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    TaskTemplate,
    derive_primary_actor,
    resolve_primary_actor,
)
from backend.app.motors.m_workflow_engine.dependency_resolver_service import (
    TERMINAL_DONE_STATUSES,
    check_dependencies_satisfied,
    resolve_step_status,
)


def _mk_task(template_id: str, status: str):
    """Helper · build task-like object sin SQLAlchemy ORM overhead."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        template_id=template_id,
        phase="diagnostico",
        title=f"Task {template_id}",
        status=status,
        priority=0,
        blocked_reason=None,
        due_date=None,
        started_at=None,
        completed_at=None,
    )


def _mk_template(
    template_id: str,
    actors: list[str] | None = None,
    primary_actor: str | None = None,
    prerequisite_template_ids: list[str] | None = None,
) -> TaskTemplate:
    return TaskTemplate(
        id=template_id,
        phase="diagnostico",
        applicable_categories="ALL",
        applicable_archetypes="ALL",
        title=f"Template {template_id}",
        actors=actors or [],
        primary_actor=primary_actor,
        prerequisite_template_ids=prerequisite_template_ids or [],
    )


# ============= derive_primary_actor =============


def test_derive_primary_actor_marcos_only_is_admin():
    assert derive_primary_actor(["Marcos"]) == "admin"


def test_derive_primary_actor_empty_is_admin():
    assert derive_primary_actor([]) == "admin"


def test_derive_primary_actor_marcos_first_is_admin():
    assert derive_primary_actor(["Marcos", "cliente_PoC"]) == "admin"


def test_derive_primary_actor_cliente_first_is_cliente():
    assert derive_primary_actor(["cliente_PoC", "responsable_TI_cliente"]) == "cliente"


def test_derive_primary_actor_ciso_first_is_cliente():
    assert derive_primary_actor(["CISO", "Marcos"]) == "cliente"


def test_derive_primary_actor_only_agents_is_system():
    """A##_xxx prefix solo → system."""
    assert derive_primary_actor(["A19_redactor_propuestas", "A21_discrepancias"]) == "system"


def test_derive_primary_actor_marcos_with_agent_still_admin():
    """Marcos + A##_ → admin (Marcos drives)."""
    assert derive_primary_actor(["Marcos", "A19_redactor_propuestas"]) == "admin"


def test_derive_primary_actor_rsegcliente_first():
    """RSEG_cliente first non-agent → cliente."""
    assert derive_primary_actor(["A4_redactor_politicas", "RSEG_cliente"]) == "cliente"


# ============= resolve_primary_actor (explícito override) =============


def test_resolve_primary_actor_explicit_overrides_derived():
    """primary_actor explícito en YAML gana sobre derive."""
    t = _mk_template("X", actors=["Marcos"], primary_actor="cliente")
    assert resolve_primary_actor(t) == "cliente"


def test_resolve_primary_actor_uses_derive_when_none():
    t = _mk_template("X", actors=["cliente_PoC"])
    assert resolve_primary_actor(t) == "cliente"


# ============= check_dependencies_satisfied =============


def test_check_deps_no_prereqs_returns_satisfied():
    t = _mk_template("X", prerequisite_template_ids=[])
    satisfied, missing = check_dependencies_satisfied(t, {})
    assert satisfied is True
    assert missing == []


def test_check_deps_prereq_done_satisfied():
    t = _mk_template("X", prerequisite_template_ids=["A"])
    tasks = {"A": _mk_task("A", "done")}
    satisfied, missing = check_dependencies_satisfied(t, tasks)
    assert satisfied is True
    assert missing == []


def test_check_deps_prereq_completed_satisfied_backward_compat():
    """Backward-compat · "completed" tratado igual que "done"."""
    t = _mk_template("X", prerequisite_template_ids=["A"])
    tasks = {"A": _mk_task("A", "completed")}
    satisfied, missing = check_dependencies_satisfied(t, tasks)
    assert satisfied is True


def test_check_deps_prereq_in_progress_NOT_satisfied():
    t = _mk_template("X", prerequisite_template_ids=["A"])
    tasks = {"A": _mk_task("A", "in_progress")}
    satisfied, missing = check_dependencies_satisfied(t, tasks)
    assert satisfied is False
    assert missing == ["A"]


def test_check_deps_prereq_missing_NOT_satisfied():
    """ClientTask NO existe yet (NO regenerate fired) → unsatisfied."""
    t = _mk_template("X", prerequisite_template_ids=["A"])
    satisfied, missing = check_dependencies_satisfied(t, {})
    assert satisfied is False
    assert missing == ["A"]


def test_check_deps_multiple_prereqs_partial():
    t = _mk_template("X", prerequisite_template_ids=["A", "B", "C"])
    tasks = {
        "A": _mk_task("A", "done"),
        "B": _mk_task("B", "pending"),
        # C missing entirely
    }
    satisfied, missing = check_dependencies_satisfied(t, tasks)
    assert satisfied is False
    assert set(missing) == {"B", "C"}


# ============= resolve_step_status =============


def test_resolve_step_done_terminal():
    t = _mk_template("X", actors=["Marcos"])
    tasks = {"X": _mk_task("X", "done")}
    res = resolve_step_status(t, tasks)
    assert res.status == "done"
    assert res.missing_prerequisites == []
    assert res.blocker_reason is None


def test_resolve_step_completed_terminal_backward_compat():
    t = _mk_template("X", actors=["Marcos"])
    tasks = {"X": _mk_task("X", "completed")}
    res = resolve_step_status(t, tasks)
    assert res.status == "done"


def test_resolve_step_in_progress():
    t = _mk_template("X", actors=["cliente_PoC"])
    tasks = {"X": _mk_task("X", "in_progress")}
    res = resolve_step_status(t, tasks)
    assert res.status == "in_progress"
    assert res.primary_actor == "cliente"


def test_resolve_step_available_no_prereqs():
    t = _mk_template("X", actors=["Marcos"])
    res = resolve_step_status(t, {})
    assert res.status == "available"
    assert res.primary_actor == "admin"


def test_resolve_step_blocked_prereq_pending():
    t = _mk_template(
        "X", actors=["cliente_PoC"], prerequisite_template_ids=["A"],
    )
    tasks = {"A": _mk_task("A", "in_progress")}
    res = resolve_step_status(t, tasks)
    assert res.status == "blocked"
    assert res.missing_prerequisites == ["A"]
    assert res.blocker_reason is not None


def test_resolve_step_blocked_single_prereq_admin_actor_friendly(monkeypatch):
    """Single prereq admin · blocker_reason "Esperando Marcos termine"."""
    monkeypatch.setattr(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_template_by_id",
        lambda tid: (
            _mk_template(tid, actors=["Marcos"]) if tid == "A" else None
        ),
    )
    t = _mk_template("X", actors=["cliente_PoC"], prerequisite_template_ids=["A"])
    res = resolve_step_status(t, {})
    assert res.status == "blocked"
    assert "Marcos" in res.blocker_reason


def test_resolve_step_blocked_single_prereq_cliente_actor_friendly(monkeypatch):
    """Single prereq cliente · blocker_reason "Esperando cliente complete"."""
    monkeypatch.setattr(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_template_by_id",
        lambda tid: (
            _mk_template(tid, actors=["cliente_PoC"]) if tid == "A" else None
        ),
    )
    t = _mk_template("X", actors=["Marcos"], prerequisite_template_ids=["A"])
    res = resolve_step_status(t, {})
    assert res.status == "blocked"
    assert "cliente" in res.blocker_reason.lower()


def test_resolve_step_blocked_multi_prereq_count(monkeypatch):
    """Multi prereq · blocker_reason describe count."""
    monkeypatch.setattr(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_template_by_id",
        lambda tid: _mk_template(tid, actors=["Marcos"]),
    )
    t = _mk_template(
        "X", actors=["Marcos"], prerequisite_template_ids=["A", "B"],
    )
    res = resolve_step_status(t, {})
    assert res.status == "blocked"
    assert "2 pasos" in res.blocker_reason


# ============= TERMINAL_DONE_STATUSES =============


def test_terminal_done_statuses_contains_both():
    """Backward-compat sostiene ambos status terminales."""
    assert "done" in TERMINAL_DONE_STATUSES
    assert "completed" in TERMINAL_DONE_STATUSES
