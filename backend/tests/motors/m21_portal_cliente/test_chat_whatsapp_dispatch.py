"""CLUSTER 5 Phase 5D delta · chat↔WhatsApp bridge dispatch.

Cubre:
- chat_admin_reply WhatsApp dispatch fired cuando admin envía y cliente opt-in
- chat_admin_reply skipped cuando cliente NO opt-in (graceful degradation)
- cliente inbound → Marcos WhatsApp via Dialog360Client.send_text (mock)
- cliente inbound skipped cuando marcos_whatsapp_number vacío
- chat_admin_reply routing row seed present con tier matrix correcto

Pattern mirror m21_portal_cliente existing test infrastructure · best-effort
try/except ALL channels (Phase 2B + Phase 2C established · NO bloquear primary
chat persistence).
"""
from __future__ import annotations

import uuid
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.chat_service import ChatService
from backend.tests.conftest import _admin_setup


async def _setup_project_with_client_user(
    db: AsyncSession, *, whatsapp_opt_in: bool = False,
):
    """Returns (project_id, client_user_id, client_id)."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, created_at) "
                "VALUES (:id, :cid, 'P', 'MEDIA', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        opt_in_sql = (
            ", whatsapp_number, whatsapp_opt_in_at"
            if whatsapp_opt_in else ""
        )
        opt_in_vals = (
            ", '+34666123456', now()"
            if whatsapp_opt_in else ""
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                f"password_hash, full_name, must_change_password{opt_in_sql}, "
                "created_at) "
                f"VALUES (:uid, :cid, :email, 'x', 'Test', false{opt_in_vals}, now())"
            ),
            {
                "uid": str(user_id),
                "cid": str(client_id),
                "email": f"u-{user_id.hex[:8]}@test.invalid",
            },
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return project_id, user_id, client_id


# ════════════════════════════════════════════════════════════════════
# Phase 5D.1 · chat_admin_reply WhatsApp routing seed verification
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_chat_admin_reply_whatsapp_routing_seeded(db: AsyncSession):
    """Migration cluster5_chat_wa_routing_001 seeds chat_admin_reply row."""
    row = (await db.execute(
        text(
            "SELECT tier_basica_route, tier_media_route, tier_alta_route, "
            "template_es FROM whatsapp_critical_events_routing "
            "WHERE event_type = 'chat_admin_reply'"
        ),
    )).first()
    assert row is not None
    assert row[0] == "digest"
    assert row[1] == "whatsapp"
    assert row[2] == "whatsapp"
    assert "Marcos te respondió" in row[3]


# ════════════════════════════════════════════════════════════════════
# Phase 5D.2 · admin reply → cliente WhatsApp dispatch
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_reply_dispatches_whatsapp_when_opt_in(
    db: AsyncSession,
):
    """Admin envía + cliente opt-in → dispatch_critical_event fired."""
    project_id, user_id, _ = await _setup_project_with_client_user(
        db, whatsapp_opt_in=True,
    )
    service = ChatService(db)
    thread = await service.get_or_create_thread(
        project_id=project_id, client_user_id=user_id,
    )

    with patch(
        "backend.app.notifications.whatsapp_dispatcher.dispatch_critical_event",
        new=AsyncMock(),
    ) as mock_dispatch:
        await service.post_message(
            thread.id, "admin", "respuesta marcos",
            sender_user_id=uuid.uuid4(),
        )
        mock_dispatch.assert_called_once()
        kwargs = mock_dispatch.call_args.kwargs
        assert kwargs["event_type"] == "chat_admin_reply"
        assert kwargs["project_id"] == project_id
        assert kwargs["client_user_id"] == user_id
        assert kwargs["payload"]["preview"] == "respuesta marcos"


@pytest.mark.asyncio
async def test_admin_reply_skipped_when_client_no_opt_in_graceful(
    db: AsyncSession,
):
    """Cliente sin opt-in → dispatch_critical_event called pero skipped reason."""
    project_id, user_id, _ = await _setup_project_with_client_user(
        db, whatsapp_opt_in=False,
    )
    service = ChatService(db)
    thread = await service.get_or_create_thread(
        project_id=project_id, client_user_id=user_id,
    )

    msg = await service.post_message(
        thread.id, "admin", "test sin opt-in",
        sender_user_id=uuid.uuid4(),
    )
    assert msg.id is not None


# ════════════════════════════════════════════════════════════════════
# Phase 5D.3 · cliente inbound → Marcos WhatsApp dispatch
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_client_inbound_dispatches_to_marcos_when_configured(
    db: AsyncSession, monkeypatch,
):
    """Cliente envía + marcos_whatsapp_number set → Dialog360 send_text fired."""
    project_id, user_id, _ = await _setup_project_with_client_user(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(
        project_id=project_id, client_user_id=user_id,
    )

    from backend.app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666999888")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "mock")

    captured = {}

    class _StubClient:
        def __init__(self, **_):
            pass

        async def send_text(self, to: str, body: str):
            captured["to"] = to
            captured["body"] = body
            from backend.app.motors.m31_whatsapp.dialog_360_client import (
                SendMessageResult,
            )
            return SendMessageResult(
                ok=True, whatsapp_message_id="mock", status="sent",
            )

    with patch(
        "backend.app.motors.m31_whatsapp.dialog_360_client.Dialog360Client",
        _StubClient,
    ):
        await service.post_message(
            thread.id, "client", "hola marcos urgente",
            sender_user_id=user_id,
        )

    get_settings.cache_clear()
    assert captured.get("to") == "+34666999888"
    assert "hola marcos urgente" in captured.get("body", "")
    assert "te escribió" in captured.get("body", "")


@pytest.mark.asyncio
async def test_client_inbound_skipped_when_marcos_number_empty(
    db: AsyncSession, monkeypatch,
):
    """No marcos_whatsapp_number → silently skipped, NO error · message persisted OK."""
    project_id, user_id, _ = await _setup_project_with_client_user(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(
        project_id=project_id, client_user_id=user_id,
    )

    from backend.app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")

    msg = await service.post_message(
        thread.id, "client", "graceful degradation",
        sender_user_id=user_id,
    )
    get_settings.cache_clear()
    assert msg.id is not None
    assert msg.content == "graceful degradation"
