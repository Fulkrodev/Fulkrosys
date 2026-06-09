"""Tests cross-motor M29 ↔ M30 + audit_log + RLS (sub-fase 6.A.9).

Cobertura cross-motor + integraciones BD-side:

  AUDIT LOG (3 tests):
    - test_audit_log_entries_on_message_insert
    - test_audit_log_entries_on_message_update_mark_read
    - test_audit_log_entries_on_attachment_insert

  RLS ISOLATION (2 tests):
    - test_rls_client_isolation_blocks_cross_client
    - test_rls_admin_role_bypass_sees_all

  M30 TIMELINE (2 tests, complementarios baseline):
    - test_m30_log_interaction_message_excerpt_truncation
    - test_m30_silent_fail_when_contact_deleted (post-send)

Ver:
  - Plan v4.2 6.6 V-CHECK puntos: "Audit log entries con hash chain" +
    "RLS verificado: cliente A no ve mensajes cliente B"
  - TODO-M29-M24-IDMS-INTEGRATION-001 (diferido a SESIÓN B frontend
    porque requiere crear DocumentFolder + Document entity completa).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m29_client_messaging.models import ClientMessage
from backend.app.motors.m29_client_messaging.schemas import (
    AdminSendMessageBody,
    ClientSendMessageBody,
)
from backend.app.motors.m29_client_messaging.service import (
    ClientMessagingService,
)
from backend.app.motors.m30_client_contacts.schemas import ClientContactCreate
from backend.app.motors.m30_client_contacts.service import (
    ClientContactService,
    ContactNotFoundError,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_test_setup(
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create client + project + client_user. Returns
    (client_id, project_id, client_user_id)."""
    from backend.app.models.client_portal import ClientUser

    client_id_str, project_id_str = await setup_test_project(db)
    client_id = uuid.UUID(client_id_str)
    project_id = uuid.UUID(project_id_str)

    cu = ClientUser(
        client_id=client_id,
        email=f"cu-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        must_change_password=False,
    )
    db.add(cu)
    await db.flush()
    await db.refresh(cu)
    return client_id, project_id, cu.id


async def _create_admin_user(db: AsyncSession) -> uuid.UUID:
    from backend.app.models.auth import User

    user = User(
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        display_name="Admin Test",
        is_active=True,
        role="owner",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user.id


# ════════════════════════════════════════════════════════════════════
# AUDIT LOG TRIGGERS — 3 tests
# ════════════════════════════════════════════════════════════════════


class TestAuditLog:

    @pytest.mark.asyncio
    async def test_audit_log_entries_on_message_insert(
        self, db: AsyncSession,
    ):
        """fn_audit_track trigger crea entry audit_log al insertar mensaje."""
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="audit me"),
        )
        # Query audit_log entries para esta tabla
        async with _admin_setup(db):
            r = await db.execute(text(
                "SELECT accion, registro_id FROM audit_log "
                "WHERE registro_id = :rid AND tabla = 'client_messages' "
                "ORDER BY timestamp"
            ), {"rid": str(msg.id)})
            rows = list(r)
        assert len(rows) >= 1
        operations = {row[0] for row in rows}
        assert "INSERT" in operations

    @pytest.mark.asyncio
    async def test_audit_log_entries_on_message_update_mark_read(
        self, db: AsyncSession,
    ):
        """Mark as read genera entry UPDATE en audit_log."""
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="msg"),
        )
        await svc.mark_as_read(message_id=msg.id, by_role="admin")

        async with _admin_setup(db):
            r = await db.execute(text(
                "SELECT accion FROM audit_log "
                "WHERE registro_id = :rid AND tabla = 'client_messages' "
                "ORDER BY timestamp"
            ), {"rid": str(msg.id)})
            ops = [row[0] for row in r]
        assert "INSERT" in ops
        assert "UPDATE" in ops

    @pytest.mark.asyncio
    async def test_audit_log_entries_on_attachment_insert(
        self, db: AsyncSession,
    ):
        """Insert attachment genera entry audit_log."""
        from backend.app.motors.m29_client_messaging.models import (
            ClientMessageAttachment,
            DEFAULT_MINIO_BUCKET,
        )

        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="msg with att"),
        )

        att = ClientMessageAttachment(
            message_id=msg.id,
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            minio_bucket=DEFAULT_MINIO_BUCKET,
            minio_object_key=f"{msg.id}/test/test.pdf",
        )
        db.add(att)
        await db.flush()

        async with _admin_setup(db):
            r = await db.execute(text(
                "SELECT accion FROM audit_log "
                "WHERE registro_id = :rid AND "
                "tabla = 'client_message_attachments' "
                "ORDER BY timestamp"
            ), {"rid": str(att.id)})
            ops = [row[0] for row in r]
        assert "INSERT" in ops


# ════════════════════════════════════════════════════════════════════
# RLS ISOLATION — 2 tests
# ════════════════════════════════════════════════════════════════════


class TestRLSIsolation:

    @pytest.mark.asyncio
    async def test_rls_client_isolation_blocks_cross_client(
        self, db: AsyncSession,
    ):
        """Cliente A con app.current_client_id NO ve mensajes cliente B."""
        from backend.app.database import set_tenant_context

        client_a, _, cu_a = await _create_test_setup(db)
        client_b, _, cu_b = await _create_test_setup(db)
        svc = ClientMessagingService(db)

        # Setear contexto cliente A antes de su INSERT (RLS post-SAN-B.MB-2.1)
        await set_tenant_context(db, client_id=client_a)
        msg_a = await svc.send_as_client(
            client_id=client_a, client_user_id=cu_a,
            payload=ClientSendMessageBody(body_markdown="A msg"),
        )
        # Switch a cliente B para su INSERT
        await set_tenant_context(db, client_id=client_b)
        msg_b = await svc.send_as_client(
            client_id=client_b, client_user_id=cu_b,
            payload=ClientSendMessageBody(body_markdown="B msg"),
        )

        # Set tenant context cliente A para query isolation test
        await set_tenant_context(db, client_id=client_a)

        # Query directa sin SET ROLE → RLS aplicado
        r = await db.execute(text(
            "SELECT id FROM client_messages WHERE deleted_at IS NULL"
        ))
        ids_visible = {uuid.UUID(str(row[0])) for row in r}

        assert msg_a.id in ids_visible, "Cliente A debe ver msg propio"
        assert msg_b.id not in ids_visible, (
            "Cliente A NO debe ver msg cliente B (RLS isolation)"
        )

    @pytest.mark.asyncio
    async def test_rls_admin_role_bypass_sees_all(
        self, db: AsyncSession,
    ):
        """SET LOCAL ROLE fulkro_app_bypassrls bypassa RLS — admin ve todos los mensajes."""
        from backend.app.database import set_tenant_context

        client_a, _, cu_a = await _create_test_setup(db)
        client_b, _, cu_b = await _create_test_setup(db)
        svc = ClientMessagingService(db)

        await set_tenant_context(db, client_id=client_a)
        msg_a = await svc.send_as_client(
            client_id=client_a, client_user_id=cu_a,
            payload=ClientSendMessageBody(body_markdown="A"),
        )
        await set_tenant_context(db, client_id=client_b)
        msg_b = await svc.send_as_client(
            client_id=client_b, client_user_id=cu_b,
            payload=ClientSendMessageBody(body_markdown="B"),
        )

        # Admin: SET LOCAL ROLE fulkro_app_bypassrls (bypass RLS)
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        r = await db.execute(text(
            "SELECT id FROM client_messages WHERE deleted_at IS NULL"
        ))
        ids = {uuid.UUID(str(row[0])) for row in r}

        assert msg_a.id in ids
        assert msg_b.id in ids


# ════════════════════════════════════════════════════════════════════
# M30 TIMELINE COMPLEMENTOS — 2 tests
# ════════════════════════════════════════════════════════════════════


class TestM30TimelineComplements:

    @pytest.mark.asyncio
    async def test_m30_log_interaction_message_excerpt_truncation(
        self, db: AsyncSession,
    ):
        """Mensaje > 200 chars genera summary truncado en M30 timeline."""
        client_id, _, _ = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)

        contact_svc = ClientContactService(db)
        contact = await contact_svc.create_contact(
            client_id,
            ClientContactCreate(
                full_name="Contact Truncate",
                email="trunc@example.com",
                role_title="DPO",
                role_category="dpo",
            ),
        )

        long_body = "Lorem ipsum dolor sit amet. " * 30  # > 600 chars
        msg_svc = ClientMessagingService(db)
        await msg_svc.send_as_admin(
            admin_user_id=admin_id,
            payload=AdminSendMessageBody(
                body_markdown=long_body,
                client_id=client_id,
                to_contact_id=contact.id,
            ),
        )

        timeline = await contact_svc.get_timeline(contact.id)
        assert len(timeline) == 1
        summary = timeline[0].summary or ""
        assert len(summary) <= 200
        assert summary.endswith("…")

    @pytest.mark.asyncio
    async def test_m30_fk_set_null_on_contact_delete_post_send(
        self, db: AsyncSession,
    ):
        """FK ON DELETE SET NULL: borrar contacto post-send mantiene
        mensaje pero ``to_contact_id`` queda NULL.

        Pattern paralelo al M12 magic_link.sent_to_contact_id (commit
        c3a8d7f2b419 BLOQUE 3 BAJAS).
        """
        client_id, _, _ = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)

        contact_svc = ClientContactService(db)
        contact = await contact_svc.create_contact(
            client_id,
            ClientContactCreate(
                full_name="To Delete Post",
                email="delete-post@example.com",
                role_title="Aux",
                role_category="otros",
            ),
        )

        msg_svc = ClientMessagingService(db)
        msg = await msg_svc.send_as_admin(
            admin_user_id=admin_id,
            payload=AdminSendMessageBody(
                body_markdown="pre-delete send",
                client_id=client_id,
                to_contact_id=contact.id,
            ),
        )
        assert msg.to_contact_id == contact.id

        # Hard-delete contacto → FK SET NULL aplicado por BD
        await contact_svc.delete_contact_cascade(contact.id)
        await db.flush()

        # Mensaje persiste, FK ahora NULL
        await db.refresh(msg)
        assert msg.id is not None
        assert msg.to_contact_id is None, (
            "FK ON DELETE SET NULL debe limpiar to_contact_id"
        )
