"""#22 Ola 5 · admin nudge scheduler · push proactivo in-app + anti-spam.

- Genera nudge para proyecto urgent que Marcos NO ha abierto (inactividad).
- Puerta de inactividad: si lo vio hace poco (audit_log copilot.hint.generated
  reciente) → NO molestar.
- Cooldown 7d: tras despachar, segunda corrida → 0 (anti-spam).
- NotificationEvent in-app con discriminador limpio (event_type) ·
  recipient_user_id NULL (la FK es a client_users) · recipient_email seteado.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.motors.m11_copiloto.admin_nudge_scheduler import (
    ADMIN_NUDGE_EVENT_TYPE,
    compute_pending_admin_nudges,
    dispatch_admin_nudges,
)
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _set_phase(db, pid: uuid.UUID, phase: WorkflowPhase) -> None:
    async with _admin_setup(db):
        await db.execute(text("SET LOCAL session_replication_role = 'replica'"))
        await db.execute(
            text("UPDATE projects SET fase = :p WHERE id = :pid"),
            {"p": phase.value, "pid": str(pid)},
        )
        await db.execute(text("SET LOCAL session_replication_role = 'origin'"))


async def _insert_recent_hint_view(db, pid: uuid.UUID) -> None:
    """Simula que Marcos abrió el copiloto del proyecto hace un momento."""
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO audit_log "
            "(id, tabla, registro_id, accion, usuario, project_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'copilot_hints', :pid, "
            "'copilot.hint.generated', 'admin', :pid, CAST('{}' AS jsonb), now())"
        ), {"pid": str(pid)})


async def test_admin_nudge_generated_for_inactive_urgent_project(db: AsyncSession):
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.IMPLANTACION)  # acción admin urgent

    nudges = await compute_pending_admin_nudges(db)
    mine = [n for n in nudges if n.project_id == project_id]
    assert len(mine) == 1, "proyecto urgent + sin actividad reciente → 1 nudge"
    assert mine[0].source_action
    assert mine[0].motor


async def test_admin_nudge_skipped_when_recently_viewed(db: AsyncSession):
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.IMPLANTACION)
    await _insert_recent_hint_view(db, pid)

    nudges = await compute_pending_admin_nudges(db)
    mine = [n for n in nudges if n.project_id == project_id]
    assert len(mine) == 0, "Marcos lo vio hace poco → no molestar (inactividad)"


async def test_admin_nudge_cooldown_anti_spam_and_event_shape(db: AsyncSession):
    _client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    await _set_phase(db, pid, WorkflowPhase.IMPLANTACION)

    nudges = await compute_pending_admin_nudges(db)
    mine = [n for n in nudges if n.project_id == project_id]
    assert len(mine) == 1

    result = await dispatch_admin_nudges(db, mine)
    assert result["dispatched"] == 1, result

    # NotificationEvent escrito · discriminador limpio + recipient correcto.
    async with _admin_setup(db):
        row = (await db.execute(text(
            "SELECT event_type, recipient_user_id, recipient_email "
            "FROM notification_events "
            "WHERE event_type = :et AND project_id = :pid"
        ), {"et": ADMIN_NUDGE_EVENT_TYPE, "pid": project_id})).fetchone()
    assert row is not None, "debe existir el NotificationEvent del nudge admin"
    assert row[0] == ADMIN_NUDGE_EVENT_TYPE
    assert row[1] is None, "recipient_user_id NULL (FK a client_users · no admin)"
    assert row[2], "recipient_email debe estar seteado (owner)"

    # Segunda corrida inmediata → cooldown 7d → 0 (anti-spam).
    nudges2 = await compute_pending_admin_nudges(db)
    mine2 = [n for n in nudges2 if n.project_id == project_id]
    assert len(mine2) == 0, "cooldown 7d → no re-nudge (anti-spam)"
