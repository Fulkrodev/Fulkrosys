"""Conversation service · CLUSTER 4 Phase 4E cross-conversation continuity.

Sesión 3B-2B.8 CLUSTER 4 Phase 4E · pure functional service per cliente
copilot conversation persistence + context preservation.

Filosofía cliente-mínimo:
- Cliente RECIBE su propio historial conversation (multi-tenant isolated)
- Cliente NO opera conversation lifecycle administrative (admin OWNS create/delete)
- Best-effort persistence (primary Q&A NUNCA bloqueado por persistence fail)

Pure functional R1 deterministic:
- get_or_create_active_conversation(): per cliente_user + project session
- persist_message(): append message + metadata
- get_recent_messages(): last N messages for context preservation
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.copilot import CopilotConversation, CopilotMessage


logger = logging.getLogger(__name__)


async def get_or_create_active_conversation(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    client_id: Optional[uuid.UUID] = None,
    titulo_default: str = "Sesión copiloto cliente",
) -> CopilotConversation:
    """Find latest conversation cliente + project · create si NO existe.

    Strategy: 1 active conversation per cliente_user + project (most recent).
    Future Phase 5 chat in-app puede separar threads multiple per cliente.
    """
    stmt = (
        select(CopilotConversation)
        .where(CopilotConversation.project_id == project_id)
        .where(CopilotConversation.client_id == client_id)
        .where(CopilotConversation.autor == str(client_user_id))
        .order_by(CopilotConversation.created_at.desc())
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    new_conv = CopilotConversation(
        project_id=project_id,
        client_id=client_id,
        titulo=titulo_default,
        autor=str(client_user_id),
    )
    db.add(new_conv)
    await db.flush()
    return new_conv


async def persist_message(
    db: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    project_id: uuid.UUID,
    role: str,
    content: str,
    citations: Optional[list] = None,
    chunk_ids_used: Optional[list] = None,
    model_used: Optional[str] = None,
    tokens_input: Optional[int] = None,
    tokens_output: Optional[int] = None,
) -> CopilotMessage:
    """Append message a conversation · best-effort caller persists.

    Args:
      role: 'user' | 'assistant' | 'system'

    Sets explicit created_at (microsecond precision) para evitar timestamp
    duplicate cuando multiple messages persist en same transaction (OPS-047
    pattern · order DESC determinístico).
    """
    if role not in ("user", "assistant", "system"):
        raise ValueError(
            f"role inválido: {role!r} · valid: user/assistant/system"
        )
    if not content or not content.strip():
        raise ValueError("content cannot be empty")

    msg = CopilotMessage(
        conversation_id=conversation_id,
        project_id=project_id,
        role=role,
        content=content,
        citations={"items": citations} if citations else None,
        chunk_ids_used={"ids": chunk_ids_used} if chunk_ids_used else None,
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        created_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_recent_messages(
    db: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    limit: int = 10,
) -> list[CopilotMessage]:
    """Get last N messages from conversation · DESC order then reverse.

    Used for cross-conversation context preservation cuando answer_question
    consume previous messages como prompt context.

    Tiebreaker id DESC para deterministic ordering cuando created_at idénticos
    (defense-in-depth · OPS-047 pattern aplicado).
    """
    if limit <= 0:
        return []

    stmt = (
        select(CopilotMessage)
        .where(CopilotMessage.conversation_id == conversation_id)
        .order_by(
            CopilotMessage.created_at.desc(),
            CopilotMessage.id.desc(),
        )
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    # Return chronological order (oldest first for prompt context)
    return list(reversed(rows))


async def list_conversations_cliente(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> list[CopilotConversation]:
    """Cliente lists own conversations (multi-tenant isolated por client_id)."""
    stmt = select(CopilotConversation).where(
        CopilotConversation.client_id == client_id,
    )
    if project_id is not None:
        stmt = stmt.where(CopilotConversation.project_id == project_id)
    stmt = stmt.order_by(CopilotConversation.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def get_conversation_for_cliente(
    db: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Optional[CopilotConversation]:
    """Get conversation con verificación multi-tenant ownership."""
    stmt = (
        select(CopilotConversation)
        .where(CopilotConversation.id == conversation_id)
        .where(CopilotConversation.client_id == client_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def persist_message_best_effort(
    db: AsyncSession,
    **kwargs,
) -> Optional[CopilotMessage]:
    """Wrapper best-effort · returns None si persistence fails.

    Used por portal_copiloto_chat + coach (primary Q&A NUNCA bloqueado).
    """
    try:
        return await persist_message(db, **kwargs)
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "persist_message best-effort failed · conversation_id=%s role=%s",
            kwargs.get("conversation_id"), kwargs.get("role"),
        )
        return None
