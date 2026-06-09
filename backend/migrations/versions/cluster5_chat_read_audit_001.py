"""Sesión 3B-2B.8 CLUSTER 5 Phase 5A delta · chat_messages.read_at + unread idx.

ADD read tracking column + partial index for inbox unread query optimization.
audit_log Sub-atom 5.A 3-way OR emission happens in ChatService.post_message +
mark_messages_read at application layer (no migration changes needed there).

OPS-045 57ª manifestation · audit-first reveals chat_messages 95% existing
(SAN-D MB-14.5 ADR-038 sand_chat_threads_001 shipped 2026-05-06). Delta is
read_at column only · NO new tables · NO schema rebuild.

Filosofía cliente-mínimo sostained: cliente lee mensajes admin → mark-read
endpoint Phase 5B updates `read_at` permitting inbox unread counter realtime.

Revision ID: cluster5_chat_read_audit_001
Revises: evidence_requests_001
Create Date: 2026-05-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cluster5_chat_read_audit_001"
down_revision: Union[str, None] = "evidence_requests_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "read_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_chat_messages_unread",
        "chat_messages",
        ["thread_id", "created_at"],
        postgresql_where=sa.text("read_at IS NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_unread", table_name="chat_messages")
    op.drop_column("chat_messages", "read_at")
