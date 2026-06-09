"""sand_chat_threads_001

SAN-D MB-14.5 · tablas chat_threads + chat_messages para
ChatService cliente↔admin (ADR-038).

Pivot SSE+REST en lugar de WebSocket (DEC-MB14-CHAT-WEBSOCKET-PIVOT
ADR-038 Deferrables): cliente envía via POST · admin via POST ·
ambos reciben updates via SSE existing dispatcher MB-13.3.

SLA tracking: thread.last_admin_response_at + thread.last_client_message_at
permiten calcular tiempo respuesta admin para alert SLA <2h.

Revision ID: sand_chat_threads_001
Revises: sand_client_tasks_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_chat_threads_001"
down_revision = "sand_client_tasks_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_threads",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column(
            "status", sa.String(20), server_default="open", nullable=False,
        ),
        sa.Column(
            "last_client_message_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_admin_response_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("messages_count", sa.Integer, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    op.create_index(
        "ix_chat_threads_project_status",
        "chat_threads",
        ["project_id", "status"],
    )

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "thread_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("sender_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata_jsonb", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    op.create_index(
        "ix_chat_messages_thread_created",
        "chat_messages",
        ["thread_id", "created_at"],
    )

    for tbl in ("chat_threads", "chat_messages"):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {tbl}_isolation ON {tbl}
                FOR ALL TO fulkro_app
                USING (project_id::text = current_setting('app.current_project_id', true))
                WITH CHECK (project_id::text = current_setting('app.current_project_id', true))
            """,
        )
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON {tbl} TO fulkro_app"
        )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS chat_messages_isolation ON chat_messages"
    )
    op.execute(
        "DROP POLICY IF EXISTS chat_threads_isolation ON chat_threads"
    )
    op.drop_index(
        "ix_chat_messages_thread_created", table_name="chat_messages",
    )
    op.drop_table("chat_messages")
    op.drop_index(
        "ix_chat_threads_project_status", table_name="chat_threads",
    )
    op.drop_table("chat_threads")
