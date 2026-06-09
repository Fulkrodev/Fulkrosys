"""#13 Ola 3 · advance_step (admin) emite step_completed al cliente en realtime.

Antes: `WorkflowEngineService.advance_step` hacía commit + return SIN dispatch →
Marcos avanzaba un sub-paso y el cliente no se enteraba hasta refrescar.
Ahora: post-commit + best-effort, emite `step_completed` con el `primary_actor`
del template (el cliente lo recibe cuando primary_actor == "admin").
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_template_by_id,
    resolve_primary_actor,
)
from backend.app.motors.m_workflow_engine.service import WorkflowEngineService
from backend.tests.conftest import setup_test_project

# Template real del catálogo · actors [Marcos, ...] → primary_actor admin.
_ADMIN_TEMPLATE_ID = "ENR_PV_02_PROPOSAL_GENERATION"


@pytest.mark.asyncio
async def test_advance_step_dispatches_step_completed(db):
    _client_id, project_id = await setup_test_project(db)
    tmpl = get_template_by_id(_ADMIN_TEMPLATE_ID)
    assert tmpl is not None, "template catalog debe contener el id de prueba"

    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service.sse_dispatcher",
        new=AsyncMock(),
    ) as mock_dispatcher:
        await WorkflowEngineService(db).advance_step(
            project_id=uuid.UUID(project_id),
            template_id=_ADMIN_TEMPLATE_ID,
            updated_by=uuid.uuid4(),
        )

    # El avance emitió step_completed al canal del proyecto (real dispatch_step_completed
    # corriendo sobre el dispatcher mockeado · prueba el wiring end-to-end).
    mock_dispatcher.dispatch.assert_awaited_once()
    kw = mock_dispatcher.dispatch.await_args.kwargs
    assert kw["channel"] == f"project:{project_id}"
    assert kw["event_type"] == "step_completed"
    assert kw["data"]["template_id"] == _ADMIN_TEMPLATE_ID
    assert kw["data"]["primary_actor"] == resolve_primary_actor(tmpl)
    assert kw["data"]["step_title"] == tmpl.title


@pytest.mark.asyncio
async def test_advance_step_sse_failure_does_not_break_advance(db):
    """BEST-EFFORT REAL: si el dispatch SSE revienta, el avance NO se revierte
    (el SSE es notificación, no transacción · try/except traga + loguea)."""
    _client_id, project_id = await setup_test_project(db)

    async def _boom(*a, **k):
        raise RuntimeError("sse boom")

    with patch(
        "backend.app.motors.m_workflow_engine.dependency_resolver_service"
        ".dispatch_step_completed",
        new=_boom,
    ):
        # NO debe propagar · el avance devuelve la task completada igualmente.
        task = await WorkflowEngineService(db).advance_step(
            project_id=uuid.UUID(project_id),
            template_id=_ADMIN_TEMPLATE_ID,
            updated_by=uuid.uuid4(),
        )

    assert task.status == "completed"
    assert task.completed_at is not None
