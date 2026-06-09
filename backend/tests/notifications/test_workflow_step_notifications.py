"""Tests · workflow_step_notifications (1.D.G.F v3.11).

Cubre:
- whatsapp_notifications_enabled feature flag default + env var override
- _format_cliente_message · usa template.notification_template_cliente o default
- _format_admin_message · idem
- send_client_unblock_notification crea ClientNotification rows in-app
- send_admin_step_completed_notification idempotente log-only (admin inbox pending)
- send_client_remind_notification reusa unblock notification
- Feature flag WHATSAPP off · skip whatsapp channel
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.motors.m21_portal_cliente.task_templates_loader import TaskTemplate
from backend.app.notifications.workflow_step_notifications import (
    _format_admin_message,
    _format_cliente_message,
    send_admin_step_completed_notification,
    send_client_unblock_notification,
    whatsapp_notifications_enabled,
)


def _mk_template(
    template_id: str = "X",
    actors: list[str] | None = None,
    notification_cliente: str | None = None,
    notification_admin: str | None = None,
) -> TaskTemplate:
    return TaskTemplate(
        id=template_id,
        phase="diagnostico",
        applicable_categories="ALL",
        applicable_archetypes="ALL",
        title=f"Template {template_id}",
        actors=actors or ["Marcos"],
        notification_template_cliente=notification_cliente,
        notification_template_admin=notification_admin,
    )


# ============= Feature flag =============


def test_whatsapp_flag_default_enabled(monkeypatch):
    monkeypatch.delenv("WHATSAPP_NOTIFICATIONS_ENABLED", raising=False)
    assert whatsapp_notifications_enabled() is True


def test_whatsapp_flag_false_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFICATIONS_ENABLED", "false")
    assert whatsapp_notifications_enabled() is False


def test_whatsapp_flag_off_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFICATIONS_ENABLED", "off")
    assert whatsapp_notifications_enabled() is False


def test_whatsapp_flag_0_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFICATIONS_ENABLED", "0")
    assert whatsapp_notifications_enabled() is False


def test_whatsapp_flag_true_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFICATIONS_ENABLED", "true")
    assert whatsapp_notifications_enabled() is True


# ============= Format helpers =============


def test_format_cliente_default_message():
    tmpl = _mk_template(template_id="X")
    msg = _format_cliente_message(tmpl)
    assert "Template X" in msg
    assert "es tu turno" in msg


def test_format_cliente_template_override():
    tmpl = _mk_template(
        template_id="X",
        notification_cliente="Hola · {step_title} ya está listo",
    )
    msg = _format_cliente_message(tmpl)
    assert "Hola · Template X ya está listo" == msg


def test_format_admin_default_message():
    tmpl = _mk_template(template_id="Y")
    msg = _format_admin_message(tmpl)
    assert "Template Y" in msg
    assert "puedes proceder" in msg


def test_format_admin_template_override():
    tmpl = _mk_template(
        template_id="Y",
        notification_admin="Cliente terminó {step_title} · revisar",
    )
    msg = _format_admin_message(tmpl)
    assert msg == "Cliente terminó Template Y · revisar"


# ============= send_admin_step_completed_notification =============


@pytest.mark.asyncio
async def test_send_admin_notification_log_only_no_inbox_yet():
    """Admin inbox NO yet implemented · expected log_only channel."""
    db_mock = AsyncMock()
    tmpl = _mk_template(template_id="X")
    result = await send_admin_step_completed_notification(
        db=db_mock, project_id=uuid.uuid4(), template=tmpl,
    )
    assert "log_only_admin_inbox_not_yet_implemented" in result.channels
    assert "admin_notifications_pending_T1_polish" in result.skipped_reasons


# ============= send_client_unblock_notification =============


@pytest.mark.asyncio
async def test_send_client_unblock_no_project_returns_skipped():
    """Project no encontrado · skipped reason returned graceful."""
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=None)  # Project missing
    tmpl = _mk_template(template_id="X")
    result = await send_client_unblock_notification(
        db=db_mock, project_id=uuid.uuid4(), template=tmpl,
    )
    assert "no_client_users_for_project" in result.skipped_reasons
    assert result.channels == []


@pytest.mark.asyncio
async def test_send_client_unblock_in_app_dispatched(monkeypatch):
    """ClientNotification rows added · in_app channel reported."""
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    # Mock Project + ClientUser
    project_mock = MagicMock()
    project_mock.client_id = client_id

    user_mock = MagicMock()
    user_mock.id = uuid.uuid4()
    user_mock.email = "cli@example.com"

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=project_mock)

    # Mock select(ClientUser) result
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=MagicMock(
        all=MagicMock(return_value=[user_mock])
    ))
    db_mock.execute = AsyncMock(return_value=result_mock)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()

    # Mock NotificationOrchestrator (avoid real email)
    with patch(
        "backend.app.notifications.workflow_step_notifications.whatsapp_notifications_enabled",
        return_value=False,
    ):
        # Patch orchestrator import inside function so it fails gracefully
        # We'll use side-effect to avoid actual email path
        async def fake_enqueue(**kwargs):
            return MagicMock(status="delivered")

        with patch(
            "backend.app.notifications.orchestrator.NotificationOrchestrator"
        ) as orch_cls:
            orch_inst = orch_cls.return_value
            orch_inst.enqueue = AsyncMock(side_effect=fake_enqueue)

            tmpl = _mk_template(template_id="X")
            result = await send_client_unblock_notification(
                db=db_mock, project_id=project_id, template=tmpl,
            )

    assert "in_app" in result.channels
    assert "email" in result.channels
    assert "whatsapp_flag_disabled" in result.skipped_reasons
    # db.add called once for ClientNotification
    db_mock.add.assert_called_once()
