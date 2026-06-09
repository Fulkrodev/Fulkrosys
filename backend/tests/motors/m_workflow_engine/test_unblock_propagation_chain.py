"""Tests · Propagation chain unblock cross-actor (1.D.G v3.11 sub-atom B).

Cubre:
- propagate_unblock identifica downstream steps unblocked
- dispatch SSE step_unblocked emite event canónico
- chain admin→cliente→admin alternating
- ya done/in_progress no se re-dispatcha
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.motors.m21_portal_cliente.task_templates_loader import TaskTemplate
from backend.app.motors.m_workflow_engine.dependency_resolver_service import (
    DependencyResolverService,
    dispatch_step_completed,
    dispatch_step_unblocked,
)


def _mk_template(
    template_id: str,
    actors: list[str] | None = None,
    prerequisite_template_ids: list[str] | None = None,
) -> TaskTemplate:
    return TaskTemplate(
        id=template_id,
        phase="diagnostico",
        applicable_categories="ALL",
        applicable_archetypes="ALL",
        title=f"Template {template_id}",
        actors=actors or ["Marcos"],
        prerequisite_template_ids=prerequisite_template_ids or [],
    )


# ============= SSE dispatchers =============


@pytest.mark.asyncio
async def test_dispatch_step_completed_emits_event():
    project_id = uuid.uuid4()
    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ) as mock_dispatcher:
        await dispatch_step_completed(
            project_id=project_id,
            template_id="X",
            primary_actor="admin",
            step_title="Test step",
        )
        mock_dispatcher.dispatch.assert_awaited_once()
        call_args = mock_dispatcher.dispatch.await_args
        assert call_args.kwargs["channel"] == f"project:{project_id}"
        assert call_args.kwargs["event_type"] == "step_completed"
        assert call_args.kwargs["data"]["template_id"] == "X"
        assert call_args.kwargs["data"]["primary_actor"] == "admin"


@pytest.mark.asyncio
async def test_dispatch_step_unblocked_emits_event_with_chain_meta():
    project_id = uuid.uuid4()
    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ) as mock_dispatcher:
        await dispatch_step_unblocked(
            project_id=project_id,
            template_id="X",
            primary_actor="cliente",
            unblocked_by_template_id="A",
            step_title="Cliente firma",
            estimated_days_to_complete=3,
        )
        mock_dispatcher.dispatch.assert_awaited_once()
        data = mock_dispatcher.dispatch.await_args.kwargs["data"]
        assert data["unblocked_by_template_id"] == "A"
        assert data["estimated_days_to_complete"] == 3
        assert data["primary_actor"] == "cliente"


# ============= propagate_unblock con mocks =============


@pytest.mark.asyncio
async def test_propagate_unblock_finds_downstream_steps():
    """Cuando A completes · B (prereq=A) becomes available."""
    project_id = uuid.uuid4()
    # Templates: A (no prereq) · B (prereq A) · C (prereq B · NOT yet unblocked)
    tmpl_a = _mk_template("A", actors=["Marcos"])
    tmpl_b = _mk_template("B", actors=["cliente_PoC"], prerequisite_template_ids=["A"])
    tmpl_c = _mk_template("C", actors=["Marcos"], prerequisite_template_ids=["B"])

    # Mock task A done · B y C not yet
    from types import SimpleNamespace

    def _mk_task_done(tid):
        return SimpleNamespace(
            id=uuid.uuid4(),
            project_id=project_id,
            template_id=tid,
            status="done",
            deleted_at=None,
        )

    db_mock = MagicMock()

    async def _load_dims(db, pid):
        return {"categoria_objetivo": "BASICA", "archetype": None}

    def _fake_get_enriched_steps(project_dims, phase_filter=None):
        return [tmpl_a, tmpl_b, tmpl_c]

    async def _fake_load_tasks(db, pid):
        return {"A": _mk_task_done("A")}

    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.load_project_dims",
        new=_load_dims,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_enriched_steps_for_project",
        new=_fake_get_enriched_steps,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service._load_tasks_by_template",
        new=_fake_load_tasks,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ) as mock_sse, patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_template_by_id",
        side_effect=lambda tid: {"A": tmpl_a, "B": tmpl_b, "C": tmpl_c}.get(tid),
    ):
        resolver = DependencyResolverService(db_mock)
        unblocked = await resolver.propagate_unblock(
            project_id=project_id,
            completed_template_id="A",
        )

    # B should be unblocked · C still blocked (prereq B not done)
    assert len(unblocked) == 1
    assert unblocked[0].template_id == "B"
    assert unblocked[0].status == "available"
    assert unblocked[0].primary_actor == "cliente"
    # SSE event dispatched per unblocked
    assert mock_sse.dispatch.await_count == 1


@pytest.mark.asyncio
async def test_propagate_unblock_no_downstream_when_orphan():
    """Step sin downstream prereq dependers → no events."""
    project_id = uuid.uuid4()
    tmpl_a = _mk_template("A", actors=["Marcos"])

    db_mock = MagicMock()

    async def _load_dims(db, pid):
        return {"categoria_objetivo": "BASICA"}

    def _fake_get_enriched_steps(project_dims, phase_filter=None):
        return [tmpl_a]

    async def _fake_load_tasks(db, pid):
        return {}

    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.load_project_dims",
        new=_load_dims,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_enriched_steps_for_project",
        new=_fake_get_enriched_steps,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service._load_tasks_by_template",
        new=_fake_load_tasks,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ) as mock_sse:
        resolver = DependencyResolverService(db_mock)
        unblocked = await resolver.propagate_unblock(
            project_id=project_id,
            completed_template_id="A",
        )
    assert unblocked == []
    mock_sse.dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_propagate_unblock_alternating_actor_chain():
    """Cadena admin→cliente→admin alternating · solo unblocks adjacent."""
    project_id = uuid.uuid4()
    tmpl_a = _mk_template("A", actors=["Marcos"])  # admin
    tmpl_b = _mk_template("B", actors=["cliente_PoC"], prerequisite_template_ids=["A"])  # cliente
    tmpl_c = _mk_template("C", actors=["Marcos"], prerequisite_template_ids=["B"])  # admin
    tmpl_d = _mk_template("D", actors=["cliente_PoC"], prerequisite_template_ids=["C"])  # cliente

    from types import SimpleNamespace

    def _mk_done(tid):
        return SimpleNamespace(
            id=uuid.uuid4(),
            project_id=project_id,
            template_id=tid,
            status="done",
            deleted_at=None,
        )

    db_mock = MagicMock()

    async def _load_dims(db, pid):
        return {"categoria_objetivo": "BASICA"}

    def _fake_steps(project_dims, phase_filter=None):
        return [tmpl_a, tmpl_b, tmpl_c, tmpl_d]

    async def _fake_load_tasks(db, pid):
        # A + B done · C still pending · D blocked by C
        return {"A": _mk_done("A"), "B": _mk_done("B")}

    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.load_project_dims",
        new=_load_dims,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_enriched_steps_for_project",
        new=_fake_steps,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service._load_tasks_by_template",
        new=_fake_load_tasks,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_template_by_id",
        side_effect=lambda tid: {
            "A": tmpl_a, "B": tmpl_b, "C": tmpl_c, "D": tmpl_d,
        }.get(tid),
    ):
        resolver = DependencyResolverService(db_mock)
        # Trigger propagation desde completing B
        unblocked = await resolver.propagate_unblock(
            project_id=project_id,
            completed_template_id="B",
        )

    # Only C unblocked (prereq B done) · D still blocked (prereq C not done)
    assert len(unblocked) == 1
    assert unblocked[0].template_id == "C"
    assert unblocked[0].primary_actor == "admin"  # alternating · admin's turn


@pytest.mark.asyncio
async def test_propagate_unblock_skips_already_done():
    """Si step downstream ya done · no re-dispatcha unblock."""
    project_id = uuid.uuid4()
    tmpl_a = _mk_template("A")
    tmpl_b = _mk_template("B", prerequisite_template_ids=["A"])

    from types import SimpleNamespace

    def _mk_done(tid):
        return SimpleNamespace(
            id=uuid.uuid4(),
            project_id=project_id,
            template_id=tid,
            status="done",
            deleted_at=None,
        )

    db_mock = MagicMock()

    async def _load_dims(db, pid):
        return {"categoria_objetivo": "BASICA"}

    def _fake_steps(project_dims, phase_filter=None):
        return [tmpl_a, tmpl_b]

    async def _fake_load_tasks(db, pid):
        return {"A": _mk_done("A"), "B": _mk_done("B")}

    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.load_project_dims",
        new=_load_dims,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_enriched_steps_for_project",
        new=_fake_steps,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service._load_tasks_by_template",
        new=_fake_load_tasks,
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ), patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.get_template_by_id",
        side_effect=lambda tid: {"A": tmpl_a, "B": tmpl_b}.get(tid),
    ):
        resolver = DependencyResolverService(db_mock)
        unblocked = await resolver.propagate_unblock(
            project_id=project_id,
            completed_template_id="A",
        )

    # B already done · resolve returns "done" · NOT "available" → skip
    assert unblocked == []
