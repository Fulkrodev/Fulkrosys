"""CLUSTER 4 Phase 4E · Cross-conversation continuity service tests.

Sesión 3B-2B.8 CLUSTER 4 Phase 4E · pure functional conversation persistence
service. Best-effort persist · context preservation for cross-conversation
continuity per cliente_user + project.

Coverage:
- get_or_create_active_conversation creates first time + reuses existing
- persist_message validates role + content + persists con metadata
- get_recent_messages returns chronological order (oldest first) · respects limit
- list_conversations_cliente multi-tenant isolated por client_id
- get_conversation_for_cliente ownership check (NO cross-tenant leak)
- persist_message_best_effort graceful fail returns None

Pattern 25 cumulative formalized: Conversation persistence + context preservation
per cliente_user + project session · best-effort persistence + multi-tenant
isolation.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m11_copiloto.conversation_service import (
    get_conversation_for_cliente,
    get_or_create_active_conversation,
    get_recent_messages,
    list_conversations_cliente,
    persist_message,
    persist_message_best_effort,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Phase 4E · get_or_create_active_conversation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_or_create_creates_first_time(db: AsyncSession) -> None:
    """First call creates conversation when none exists."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id_uuid = uuid.UUID(client_id_str)
    user_id = uuid.uuid4()

    conv = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        client_id=client_id_uuid,
    )

    assert conv.id is not None
    assert conv.project_id == project_uuid
    assert conv.client_id == client_id_uuid
    assert conv.autor == str(user_id)
    assert conv.titulo == "Sesión copiloto cliente"


@pytest.mark.asyncio
async def test_get_or_create_reuses_existing(db: AsyncSession) -> None:
    """Second call returns SAME conversation (existing per cliente+project)."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id_uuid = uuid.UUID(client_id_str)
    user_id = uuid.uuid4()

    conv1 = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        client_id=client_id_uuid,
    )
    conv2 = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=user_id,
        client_id=client_id_uuid,
    )

    assert conv1.id == conv2.id  # SAME conversation


# ════════════════════════════════════════════════════════════════════
# Phase 4E · persist_message + validation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_persist_message_validates_role(db: AsyncSession) -> None:
    """persist_message raises ValueError si role inválido."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    conv = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=uuid.uuid4(),
        client_id=uuid.UUID(client_id_str),
    )

    with pytest.raises(ValueError, match="role inválido"):
        await persist_message(
            db,
            conversation_id=conv.id,
            project_id=project_uuid,
            role="invalid_role",
            content="test",
        )


@pytest.mark.asyncio
async def test_persist_message_validates_content_empty(
    db: AsyncSession,
) -> None:
    """persist_message raises ValueError cuando content empty."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    conv = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=uuid.uuid4(),
        client_id=uuid.UUID(client_id_str),
    )

    with pytest.raises(ValueError, match="content cannot be empty"):
        await persist_message(
            db,
            conversation_id=conv.id,
            project_id=project_uuid,
            role="user",
            content="   ",
        )


@pytest.mark.asyncio
async def test_persist_message_happy_path(db: AsyncSession) -> None:
    """persist_message persists con metadata (citations · model · tokens)."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    conv = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=uuid.uuid4(),
        client_id=uuid.UUID(client_id_str),
    )

    msg = await persist_message(
        db,
        conversation_id=conv.id,
        project_id=project_uuid,
        role="assistant",
        content="Esto es una respuesta.",
        citations=["RD 311/2022 art.10"],
        model_used="claude-sonnet-4-5-20250929",
        tokens_input=120,
        tokens_output=85,
    )

    assert msg.id is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "assistant"
    assert msg.content == "Esto es una respuesta."
    assert msg.model_used == "claude-sonnet-4-5-20250929"
    assert msg.tokens_input == 120
    assert msg.tokens_output == 85
    assert msg.citations == {"items": ["RD 311/2022 art.10"]}


# ════════════════════════════════════════════════════════════════════
# Phase 4E · get_recent_messages context preservation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_recent_messages_chronological_order(
    db: AsyncSession,
) -> None:
    """get_recent_messages returns oldest-first (chronological) · respects limit."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    conv = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=uuid.uuid4(),
        client_id=uuid.UUID(client_id_str),
    )

    # Persist 3 messages
    for idx, content in enumerate(["mensaje 1", "mensaje 2", "mensaje 3"]):
        await persist_message(
            db,
            conversation_id=conv.id,
            project_id=project_uuid,
            role="user" if idx % 2 == 0 else "assistant",
            content=content,
        )

    messages = await get_recent_messages(db, conversation_id=conv.id, limit=10)
    assert len(messages) == 3
    assert messages[0].content == "mensaje 1"
    assert messages[-1].content == "mensaje 3"


@pytest.mark.asyncio
async def test_get_recent_messages_respects_limit(
    db: AsyncSession,
) -> None:
    """get_recent_messages limit=2 returns last 2 chronologically."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    conv = await get_or_create_active_conversation(
        db,
        project_id=project_uuid,
        client_user_id=uuid.uuid4(),
        client_id=uuid.UUID(client_id_str),
    )

    for idx in range(5):
        await persist_message(
            db,
            conversation_id=conv.id,
            project_id=project_uuid,
            role="user",
            content=f"msg {idx}",
        )

    messages = await get_recent_messages(db, conversation_id=conv.id, limit=2)
    assert len(messages) == 2
    # Last 2 messages chronologically (msg 3 + msg 4)
    assert messages[0].content == "msg 3"
    assert messages[1].content == "msg 4"


@pytest.mark.asyncio
async def test_get_recent_messages_zero_limit_returns_empty(
    db: AsyncSession,
) -> None:
    """get_recent_messages limit=0 returns []."""
    messages = await get_recent_messages(
        db, conversation_id=uuid.uuid4(), limit=0,
    )
    assert messages == []


# ════════════════════════════════════════════════════════════════════
# Phase 4E · Multi-tenant isolation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_conversations_cliente_multi_tenant_isolated(
    db: AsyncSession,
) -> None:
    """list_conversations_cliente NEVER leaks cross-tenant conversations.

    Cross-tenant verification requires bypass RLS via _admin_setup (superuser
    role) para query both tenants simultáneamente. Endpoint cliente RLS-protected
    naturally (require_client_user enforces own session client_id).
    """
    client_a_str, project_a_str = await setup_test_project(db)
    client_a_id = uuid.UUID(client_a_str)
    project_a_id = uuid.UUID(project_a_str)
    # Create conversation A while RLS set to client A (from setup_test_project)
    await get_or_create_active_conversation(
        db,
        project_id=project_a_id,
        client_user_id=uuid.uuid4(),
        client_id=client_a_id,
    )

    client_b_str, project_b_str = await setup_test_project(db)
    client_b_id = uuid.UUID(client_b_str)
    project_b_id = uuid.UUID(project_b_str)
    # Now RLS set to client B
    await get_or_create_active_conversation(
        db,
        project_id=project_b_id,
        client_user_id=uuid.uuid4(),
        client_id=client_b_id,
    )

    # Verify cross-tenant isolation using _admin_setup (bypass RLS)
    async with _admin_setup(db):
        convs_a = await list_conversations_cliente(db, client_id=client_a_id)
        convs_b = await list_conversations_cliente(db, client_id=client_b_id)

    assert len(convs_a) >= 1
    assert all(c.client_id == client_a_id for c in convs_a), (
        "Cross-tenant leak: client A query returns client B conversations"
    )
    assert len(convs_b) >= 1
    assert all(c.client_id == client_b_id for c in convs_b)


@pytest.mark.asyncio
async def test_get_conversation_for_cliente_ownership_enforced(
    db: AsyncSession,
) -> None:
    """get_conversation_for_cliente returns None cuando client_id NOT matches."""
    client_a_str, project_a_str = await setup_test_project(db)
    conv_a = await get_or_create_active_conversation(
        db,
        project_id=uuid.UUID(project_a_str),
        client_user_id=uuid.uuid4(),
        client_id=uuid.UUID(client_a_str),
    )

    # Try fetch from different client_id · MUST return None
    result_other_tenant = await get_conversation_for_cliente(
        db,
        conversation_id=conv_a.id,
        client_id=uuid.uuid4(),  # different client
    )
    assert result_other_tenant is None

    # Same client_id · returns conversation
    result_own = await get_conversation_for_cliente(
        db,
        conversation_id=conv_a.id,
        client_id=uuid.UUID(client_a_str),
    )
    assert result_own is not None
    assert result_own.id == conv_a.id


# ════════════════════════════════════════════════════════════════════
# Phase 4E · best-effort persistence wrapper
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_persist_message_best_effort_returns_none_on_fail(
    db: AsyncSession,
) -> None:
    """persist_message_best_effort returns None when underlying fails (graceful)."""
    # Pass invalid role · underlying raises ValueError · wrapper catches
    result = await persist_message_best_effort(
        db,
        conversation_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        role="invalid_role",
        content="test",
    )
    assert result is None
