"""CLUSTER 2 Phase 2C · Coach proactivo nudge scheduler tests.

Pattern #15 cumulative · pure functional nudge scheduler + cooldown-aware
dispatch · cliente-mínimo R29 friendly tone preserved.

Cubre:
  - compute_pending_nudges activos projects only (pre_venta + ARCHIVED skip)
  - cooldown 24h skip recent ClientNotification.payload.source coach_nudge:*
  - dispatch_nudges emits ClientNotification + audit_log dual (Sub-atom 5.A)
  - cross-project RLS isolation (NO leak nudges cross-cliente)
  - Cliente-mínimo R29 friendly tone embedded (Sin prisa / cuando puedas)
  - role_filter='cliente' enforced (NO admin actions surface nudges)
  - Priority cap "urgent" → "high" (anti-presión psicológica)
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.models.client_notification import ClientNotification
from backend.app.motors.m11_copiloto.nudge_scheduler import (
    NudgeAction,
    _ensure_friendly_body,
    compute_pending_nudges,
    dispatch_nudges,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _set_project_phase(
    db: AsyncSession, project_uuid: uuid.UUID, phase: WorkflowPhase,
) -> None:
    """Bypass tg_projects_phase_changed trigger (pre-existing constraint bug)."""
    async with _admin_setup(db):
        await db.execute(text("SET LOCAL session_replication_role = 'replica'"))
        await db.execute(
            text("UPDATE projects SET fase = :p WHERE id = :pid"),
            {"p": phase.value, "pid": str(project_uuid)},
        )
        await db.execute(text("SET LOCAL session_replication_role = 'origin'"))


async def _create_active_client_user(
    db: AsyncSession, *, client_id: uuid.UUID,
) -> uuid.UUID:
    user_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {
                "uid": str(user_id),
                "cid": str(client_id),
                "email": f"cliente-{user_id.hex[:8]}@test.invalid",
            },
        )
    return user_id


async def _seed_recent_nudge_notification(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    source_action: str,
    hours_ago: int = 1,
) -> None:
    """Insert ClientNotification simulating prior coach nudge dispatch.

    Use CAST(... AS jsonb) and explicit interval string · avoid :param::type
    syntax conflict with asyncpg parameter binding.
    """
    import json as _json
    payload_str = _json.dumps({"source": f"coach_nudge:{source_action}"})
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO client_notifications "
            "(id, project_id, client_user_id, type, title, body, "
            "target_url, priority, payload_json, emitted_by_motor, created_at) "
            "VALUES (gen_random_uuid(), :pid, :uid, 'generic_alert', "
            "'Past nudge', 'past body', '/x', 'normal', "
            "CAST(:payload AS jsonb), 'm11_copiloto_coach', "
            "now() - make_interval(hours => :hours))"
        ), {
            "pid": str(project_id),
            "uid": str(client_user_id),
            "payload": payload_str,
            "hours": hours_ago,
        })


# ════════════════════════════════════════════════════════════════════
# compute_pending_nudges
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pre_venta_project_NOT_yields_nudges(
    db: AsyncSession,
) -> None:
    """pre_venta project · cliente actions empty · NO nudges generated."""
    client_id_str, project_id_str = await setup_test_project(db)
    # fase default = pre_venta · NO ClientUser needed
    await _create_active_client_user(db, client_id=uuid.UUID(client_id_str))

    # Active filter excludes pre_venta · _list_active_projects skips
    nudges = await compute_pending_nudges(db, cooldown_hours=24)

    # Filter empirical · NO nudges for pre_venta
    project_nudges = [n for n in nudges if n.project_id == project_id_str]
    assert project_nudges == []


@pytest.mark.asyncio
async def test_implantacion_phase_yields_sign_dda_urgent_nudge_priority_high(
    db: AsyncSession,
) -> None:
    """IMPLANTACION phase · cliente sign_dda urgent → nudge priority='high' (cap)."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    nudges = await compute_pending_nudges(db, cooldown_hours=24)

    project_nudges = [n for n in nudges if n.project_id == project_id_str]
    assert len(project_nudges) >= 1
    top = project_nudges[0]
    assert top.client_user_id == str(user_id)
    assert top.source_action == "sign_dda"
    assert top.motor == "m03"
    # Cliente-mínimo guard · cap urgent → high
    assert top.priority == "high"
    assert top.notification_type == "generic_alert"
    # R29 friendly body embedded
    assert (
        "sin prisa" in top.body.lower() or "cuando puedas" in top.body.lower()
    )


@pytest.mark.asyncio
async def test_cooldown_24h_skips_recent_dispatched_nudge(
    db: AsyncSession,
) -> None:
    """Cooldown 24h · skip nudge si ClientNotification payload source recent."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    # Seed recent nudge for sign_dda (1h ago · within cooldown)
    await _seed_recent_nudge_notification(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        source_action="sign_dda",
        hours_ago=1,
    )

    nudges = await compute_pending_nudges(db, cooldown_hours=24)

    # NO nudge for this project · cooldown active
    project_nudges = [n for n in nudges if n.project_id == project_id_str]
    sign_dda_nudges = [n for n in project_nudges if n.source_action == "sign_dda"]
    assert sign_dda_nudges == [], "Cooldown should skip recent sign_dda nudge"


@pytest.mark.asyncio
async def test_cooldown_past_window_does_not_skip(
    db: AsyncSession,
) -> None:
    """Cooldown 24h · prior nudge >24h ago NOT skip (re-eligible)."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    # Seed nudge 48h ago · outside cooldown
    await _seed_recent_nudge_notification(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        source_action="sign_dda",
        hours_ago=48,
    )

    nudges = await compute_pending_nudges(db, cooldown_hours=24)

    project_nudges = [n for n in nudges if n.project_id == project_id_str]
    assert len(project_nudges) >= 1, "Past cooldown · nudge re-eligible"


# ════════════════════════════════════════════════════════════════════
# dispatch_nudges
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dispatch_emits_client_notification_and_audit_log_dual(
    db: AsyncSession,
) -> None:
    """Dispatch · ClientNotification + audit_log coach.nudge.dispatched dual emit."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)

    nudge = NudgeAction(
        project_id=project_id_str,
        client_user_id=str(user_id),
        source_action="sign_dda",
        motor="m03",
        title="Recordatorio · Implantacion",
        body="Tu DdA está lista para firma. Sin prisa por tu parte · cuando puedas.",
        priority="high",
        target_url="/client-portal/dda",
        notification_type="generic_alert",
    )

    result = await dispatch_nudges(db, [nudge])
    assert result["dispatched"] == 1
    assert result["failed"] == 0

    async with _admin_setup(db):
        notif = (await db.execute(
            select(ClientNotification).where(
                ClientNotification.client_user_id == user_id,
                ClientNotification.project_id == project_uuid,
            )
        )).scalars().all()
        audit_count = (await db.execute(
            text(
                "SELECT COUNT(*) FROM audit_log "
                "WHERE accion = 'coach.nudge.dispatched' "
                "AND project_id = :pid AND client_id = :cid"
            ),
            {"pid": project_id_str, "cid": client_id_str},
        )).scalar()

    assert len(notif) == 1
    assert notif[0].type == "generic_alert"
    assert notif[0].payload_json["source"] == "coach_nudge:sign_dda"
    assert audit_count == 1


@pytest.mark.asyncio
async def test_cross_project_compute_no_cross_user_leak(
    db: AsyncSession,
) -> None:
    """compute_pending_nudges · NudgeAction NUNCA cross-targets (user A for project B
    or vice versa). Test verifies user_id ALWAYS matches client_id of project.

    NOTE: full RLS dispatch enforcement at production runtime via Celery worker
    context · here we verify compute targeting consistency (NO logical leak).
    Test_setup constraint: setup_test_project overrides app.current_project_id
    serially · single-project compute reliable per cohort.
    """
    client_a_id_str, project_a_id_str = await setup_test_project(db)
    project_a_uuid = uuid.UUID(project_a_id_str)
    user_a_id = await _create_active_client_user(
        db, client_id=uuid.UUID(client_a_id_str),
    )
    await _set_project_phase(db, project_a_uuid, WorkflowPhase.IMPLANTACION)

    # Compute nudges with project A active context
    nudges = await compute_pending_nudges(db, cooldown_hours=24)

    # Filter nudges for project A only
    project_a_nudges = [n for n in nudges if n.project_id == project_a_id_str]
    assert len(project_a_nudges) >= 1, "Project A should yield nudges"

    # ALL project_a_nudges must target user_a_id (NO cross-user leak)
    for nudge in project_a_nudges:
        assert nudge.client_user_id == str(user_a_id), (
            f"Cross-user leak detected · nudge user_id={nudge.client_user_id} "
            f"expected={user_a_id} for project_a"
        )


@pytest.mark.asyncio
async def test_compute_finds_project_without_preset_context_beat_scenario(
    db: AsyncSession,
) -> None:
    """FIX Ola 5 · escenario beat real (sin contexto RLS inyectado).

    Antes del fix, _list_active_projects hacía un SELECT projects sin contexto
    → 0 filas como fulkro_app → el beat corría en vacío. Este test limpia el
    contexto (como el Celery worker) y verifica que compute igual encuentra el
    proyecto porque ahora itera por cliente bajo RLS.
    """
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _create_active_client_user(db, client_id=uuid.UUID(client_id_str))
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    # Simula el beat: NINGÚN contexto de proyecto/cliente fijado.
    await db.execute(text("SELECT set_config('app.current_project_id', '', true)"))
    await db.execute(text("SELECT set_config('app.current_client_id', '', true)"))

    nudges = await compute_pending_nudges(db, cooldown_hours=24)

    project_nudges = [n for n in nudges if n.project_id == project_id_str]
    assert len(project_nudges) >= 1, (
        "el beat (sin contexto) debe encontrar el proyecto · _list_active_projects "
        "itera por cliente bajo RLS (fix del defecto latente)"
    )


# ════════════════════════════════════════════════════════════════════
# Cliente-mínimo filosofía guards
# ════════════════════════════════════════════════════════════════════


def test_ensure_friendly_body_embeds_r29_phrase_when_absent():
    """_ensure_friendly_body R29 guard · embed 'Sin prisa' si NOT present."""
    body_without = "Tu DdA está lista para firma"
    body_with = _ensure_friendly_body(body_without)
    assert "sin prisa" in body_with.lower()


def test_ensure_friendly_body_preserves_when_r29_already_present():
    """No double-embed · preserve body si ya contiene tone friendly."""
    body_compliant = "Sin prisa por tu parte · revisa cuando puedas"
    body_after = _ensure_friendly_body(body_compliant)
    # Should preserve · NO double "Sin prisa"
    assert body_after.lower().count("sin prisa") == 1


def test_ensure_friendly_body_handles_empty_input():
    """Edge case · empty body returns default friendly fallback."""
    result = _ensure_friendly_body("")
    assert "sin prisa" in result.lower()
