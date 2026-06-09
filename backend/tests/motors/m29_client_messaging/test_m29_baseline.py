"""Tests baseline Motor 29 — Client Messaging (sub-fase 6.A.8).

17 tests cubren:
  Service CLIENTE:
   1. test_client_send_creates_thread (nuevo thread_id)
   2. test_client_reply_existing_thread (reuse thread_id)
   3. test_client_reply_other_thread_raises (ThreadOwnershipError)

  Service ADMIN:
   4. test_admin_new_thread_with_client_id
   5. test_admin_reply_existing_thread (deriva client_id del thread)
   6. test_admin_send_with_to_contact_logs_m30 (cross-motor)
   7. test_admin_send_without_contact_no_log
   8. test_admin_send_no_client_id_raises_permission

  List + queries:
   9. test_list_threads_for_client_returns_summary
  10. test_list_threads_for_admin_only_unread_filter
  11. test_search_full_text_admin_finds_match

  Mark read + counts:
  12. test_mark_as_read_admin_idempotent
  13. test_mark_as_read_client_wrong_role_noop
  14. test_unread_count_admin
  15. test_unread_count_client_requires_client_id

  Soft delete:
  16. test_soft_delete_owner_ok
  17. test_soft_delete_admin_moderating_ok
  18. test_soft_delete_other_client_raises_permission
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m29_client_messaging.models import (
    ClientMessage,
    ClientMessageAttachment,
)
from backend.app.motors.m29_client_messaging.schemas import (
    AdminSendMessageBody,
    ClientSendMessageBody,
)
from backend.app.motors.m29_client_messaging.service import (
    ClientMessagingService,
    MessageNotFoundError,
    MessagePermissionError,
    ThreadNotFoundError,
    ThreadOwnershipError,
)
from backend.app.motors.m30_client_contacts.models import (
    ClientContactInteraction,
)
from backend.app.motors.m30_client_contacts.schemas import ClientContactCreate
from backend.app.motors.m30_client_contacts.service import ClientContactService
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_test_setup(
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create client + project + client_user via ORM. Returns
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
    """Create auth_user role=owner via ORM. Returns user_id."""
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
# SERVICE CLIENTE — 3 tests
# ════════════════════════════════════════════════════════════════════


class TestClientSend:

    @pytest.mark.asyncio
    async def test_client_send_creates_thread(self, db: AsyncSession):
        """Nuevo mensaje sin thread_id genera UUID nuevo."""
        client_id, project_id, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)

        msg = await svc.send_as_client(
            client_id=client_id,
            client_user_id=cu_id,
            payload=ClientSendMessageBody(
                body_markdown="Hola Marcos, primer mensaje.",
                project_id=project_id,
            ),
        )
        assert msg.thread_id is not None
        assert msg.from_role == "client"
        assert msg.from_user_id == cu_id
        assert msg.client_id == client_id
        assert msg.is_read_by_client is True  # auto-read sender propio
        assert msg.is_read_by_admin is False
        assert msg.body_html  # render server-side default

    @pytest.mark.asyncio
    async def test_client_reply_existing_thread(self, db: AsyncSession):
        """Reply con thread_id existing reusa el ID."""
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)

        first = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="primer"),
        )
        reply = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(
                body_markdown="reply mismo thread",
                thread_id=first.thread_id,
            ),
        )
        assert reply.thread_id == first.thread_id
        assert reply.id != first.id

    @pytest.mark.asyncio
    async def test_client_reply_other_thread_raises(
        self, db: AsyncSession,
    ):
        """Cliente A intenta reply en thread cliente B → ThreadOwnership."""
        client_a, _, cu_a = await _create_test_setup(db)
        client_b, _, cu_b = await _create_test_setup(db)
        svc = ClientMessagingService(db)

        msg_b = await svc.send_as_client(
            client_id=client_b, client_user_id=cu_b,
            payload=ClientSendMessageBody(body_markdown="msg b"),
        )

        with pytest.raises(ThreadOwnershipError):
            await svc.send_as_client(
                client_id=client_a, client_user_id=cu_a,
                payload=ClientSendMessageBody(
                    body_markdown="reply hostil",
                    thread_id=msg_b.thread_id,
                ),
            )


# ════════════════════════════════════════════════════════════════════
# SERVICE ADMIN — 5 tests (incl M30 cross-motor)
# ════════════════════════════════════════════════════════════════════


class TestAdminSend:

    @pytest.mark.asyncio
    async def test_admin_new_thread_with_client_id(self, db: AsyncSession):
        """Admin nuevo thread requiere client_id."""
        client_id, _, _ = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)
        svc = ClientMessagingService(db)

        msg = await svc.send_as_admin(
            admin_user_id=admin_id,
            payload=AdminSendMessageBody(
                body_markdown="msg admin nuevo thread",
                client_id=client_id,
            ),
        )
        assert msg.from_role == "admin"
        assert msg.client_id == client_id
        assert msg.is_read_by_admin is True
        assert msg.is_read_by_client is False
        assert msg.thread_id is not None

    @pytest.mark.asyncio
    async def test_admin_reply_existing_thread(self, db: AsyncSession):
        """Admin reply en thread existing deriva client_id."""
        client_id, _, cu_id = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)
        svc = ClientMessagingService(db)

        first = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="cliente"),
        )
        reply = await svc.send_as_admin(
            admin_user_id=admin_id,
            payload=AdminSendMessageBody(
                body_markdown="admin reply",
                thread_id=first.thread_id,
                # client_id omitido — debe derivarse
            ),
        )
        assert reply.thread_id == first.thread_id
        assert reply.client_id == client_id

    @pytest.mark.asyncio
    async def test_admin_send_with_to_contact_logs_m30(
        self, db: AsyncSession,
    ):
        """Admin send con to_contact_id → log_interaction M30 en timeline."""
        client_id, _, _ = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)

        contact_svc = ClientContactService(db)
        contact = await contact_svc.create_contact(
            client_id,
            ClientContactCreate(
                full_name="Contact M29 Test",
                email="contact-m29@example.com",
                role_title="CFO",
                role_category="sponsor",
            ),
        )

        msg_svc = ClientMessagingService(db)
        msg = await msg_svc.send_as_admin(
            admin_user_id=admin_id,
            payload=AdminSendMessageBody(
                body_markdown="Mensaje admin con M30 picker",
                client_id=client_id,
                to_contact_id=contact.id,
            ),
        )
        assert msg.to_contact_id == contact.id

        # Verificar interaction registrada en timeline contacto
        timeline = await contact_svc.get_timeline(contact.id)
        assert len(timeline) == 1
        entry = timeline[0]
        assert entry.interaction_type == "message"
        assert entry.source_motor == "m29"
        assert entry.source_id == msg.id

    @pytest.mark.asyncio
    async def test_admin_send_without_contact_no_log(
        self, db: AsyncSession,
    ):
        """Admin send sin to_contact_id → 0 interactions creadas."""
        client_id, _, _ = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)

        contact_svc = ClientContactService(db)
        contact = await contact_svc.create_contact(
            client_id,
            ClientContactCreate(
                full_name="Contact NoLink",
                email="no-link-m29@example.com",
                role_title="CTO",
                role_category="cto",
            ),
        )

        msg_svc = ClientMessagingService(db)
        msg = await msg_svc.send_as_admin(
            admin_user_id=admin_id,
            payload=AdminSendMessageBody(
                body_markdown="Sin contact",
                client_id=client_id,
            ),
        )

        # 0 interactions con source_id == msg.id
        res = await db.execute(
            select(ClientContactInteraction).where(
                ClientContactInteraction.source_id == msg.id,
            )
        )
        assert list(res.scalars()) == []
        # Y timeline contact vacío
        timeline = await contact_svc.get_timeline(contact.id)
        assert timeline == []

    @pytest.mark.asyncio
    async def test_admin_send_no_client_id_raises_permission(
        self, db: AsyncSession,
    ):
        """Admin nuevo thread sin client_id ni thread_id → MessagePermissionError."""
        admin_id = await _create_admin_user(db)
        svc = ClientMessagingService(db)

        with pytest.raises(MessagePermissionError):
            await svc.send_as_admin(
                admin_user_id=admin_id,
                payload=AdminSendMessageBody(body_markdown="sin nada"),
            )


# ════════════════════════════════════════════════════════════════════
# LIST + SEARCH — 3 tests
# ════════════════════════════════════════════════════════════════════


class TestListsAndSearch:

    @pytest.mark.asyncio
    async def test_list_threads_for_client_returns_summary(
        self, db: AsyncSession,
    ):
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(
                body_markdown="x" * 250,  # > 200 chars excerpt
            ),
        )
        threads = await svc.list_threads_for_client(client_id=client_id)
        assert len(threads) == 1
        t = threads[0]
        assert t.thread_id == msg.thread_id
        assert t.client_id == client_id
        assert t.total_messages == 1
        assert t.unread_for_admin == 1  # cliente envió, admin no leído
        assert t.unread_for_client == 0
        assert len(t.last_message_excerpt) <= 200
        assert t.last_message_excerpt.endswith("…")

    @pytest.mark.asyncio
    async def test_list_threads_for_admin_only_unread_filter(
        self, db: AsyncSession,
    ):
        """only_unread=True excluye threads con todos read."""
        client_id, _, cu_id = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)
        svc = ClientMessagingService(db)

        msg1 = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="thread A"),
        )
        msg2 = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="thread B"),
        )
        # mark thread A como read by admin
        await svc.mark_as_read(message_id=msg1.id, by_role="admin")

        threads_unread = await svc.list_threads_for_admin(only_unread=True)
        thread_ids = {t.thread_id for t in threads_unread}
        assert msg2.thread_id in thread_ids
        assert msg1.thread_id not in thread_ids

    @pytest.mark.asyncio
    async def test_search_full_text_admin_finds_match(
        self, db: AsyncSession,
    ):
        """Search GIN encuentra mensajes por keyword español."""
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)

        await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(
                body_markdown="Necesito información sobre certificación ENS."
            ),
        )
        await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="Hola buenas"),
        )

        results = await svc.search_messages_admin(query="certificación")
        assert len(results) == 1
        assert "certificación" in results[0].body_markdown.lower()


# ════════════════════════════════════════════════════════════════════
# MARK READ + UNREAD COUNT — 4 tests
# ════════════════════════════════════════════════════════════════════


class TestMarkReadAndCounts:

    @pytest.mark.asyncio
    async def test_mark_as_read_admin_idempotent(self, db: AsyncSession):
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="mark me"),
        )
        m1 = await svc.mark_as_read(message_id=msg.id, by_role="admin")
        assert m1.is_read_by_admin is True
        # idempotente
        m2 = await svc.mark_as_read(message_id=msg.id, by_role="admin")
        assert m2.is_read_by_admin is True

    @pytest.mark.asyncio
    async def test_mark_as_read_client_wrong_role_noop(
        self, db: AsyncSession,
    ):
        """Cliente intenta marcar mensaje cliente own → no efecto (no raises)."""
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="own"),
        )
        # cliente intenta marcar propio msg from_role='client' → noop
        result = await svc.mark_as_read(message_id=msg.id, by_role="client")
        assert result.is_read_by_admin is False
        assert result.is_read_by_client is True  # ya estaba True

    @pytest.mark.asyncio
    async def test_unread_count_admin(self, db: AsyncSession):
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="m1"),
        )
        await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="m2"),
        )
        count = await svc.get_unread_count(for_role="admin")
        assert count.unread_total == 2
        assert count.unread_threads == 2

    @pytest.mark.asyncio
    async def test_unread_count_client_requires_client_id(
        self, db: AsyncSession,
    ):
        svc = ClientMessagingService(db)
        with pytest.raises(MessagePermissionError):
            await svc.get_unread_count(for_role="client", client_id=None)


# ════════════════════════════════════════════════════════════════════
# SOFT DELETE — 3 tests
# ════════════════════════════════════════════════════════════════════


class TestSoftDelete:

    @pytest.mark.asyncio
    async def test_soft_delete_owner_ok(self, db: AsyncSession):
        client_id, _, cu_id = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="me"),
        )
        await svc.soft_delete_message(
            message_id=msg.id, by_user_id=cu_id, by_role="client",
        )
        # Refrescar y verificar deleted_at
        await db.refresh(msg)
        assert msg.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_admin_moderating_ok(
        self, db: AsyncSession,
    ):
        """Admin puede borrar mensaje del cliente (moderación)."""
        client_id, _, cu_id = await _create_test_setup(db)
        admin_id = await _create_admin_user(db)
        svc = ClientMessagingService(db)
        msg = await svc.send_as_client(
            client_id=client_id, client_user_id=cu_id,
            payload=ClientSendMessageBody(body_markdown="hate speech?"),
        )
        await svc.soft_delete_message(
            message_id=msg.id, by_user_id=admin_id, by_role="admin",
        )
        await db.refresh(msg)
        assert msg.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_other_client_raises_permission(
        self, db: AsyncSession,
    ):
        """Cliente intenta borrar mensaje de otro cliente → MessagePermission."""
        client_a, _, cu_a = await _create_test_setup(db)
        client_b, _, cu_b = await _create_test_setup(db)
        svc = ClientMessagingService(db)
        msg_b = await svc.send_as_client(
            client_id=client_b, client_user_id=cu_b,
            payload=ClientSendMessageBody(body_markdown="b msg"),
        )
        with pytest.raises(MessagePermissionError):
            await svc.soft_delete_message(
                message_id=msg_b.id, by_user_id=cu_a, by_role="client",
            )
