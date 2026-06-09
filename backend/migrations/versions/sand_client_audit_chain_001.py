"""sand_client_audit_chain_001

SAN-D MB-14.1 · ALTER client_user_audit ADD columns hash chain
(DEC-MB14-1 Opcion A · backward compat 100%).

Columns añadidas (todas nullable):
- project_id UUID         · FK projects · NULL para rows pre-MB-14
- chain_index INTEGER     · monotonic per project · NULL pre-MB-14
- prev_hash VARCHAR(64)   · SHA-256 hex prev row · NULL para chain_index=0
- current_hash VARCHAR(64) · SHA-256 hex this row · UNIQUE
- session_id VARCHAR(64)
- user_agent VARCHAR(500)
- action_type VARCHAR(50) · alias semántico action

Verificación chain integrity opera SOLO sobre rows con
chain_index NOT NULL para project_id consultado.

Revision ID: sand_client_audit_chain_001
Revises: sand_audit_dry_run_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "sand_client_audit_chain_001"
down_revision = "sand_audit_dry_run_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_user_audit",
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "client_user_audit",
        sa.Column("chain_index", sa.Integer, nullable=True),
    )
    op.add_column(
        "client_user_audit",
        sa.Column("prev_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "client_user_audit",
        sa.Column("current_hash", sa.String(64), nullable=True, unique=True),
    )
    op.add_column(
        "client_user_audit",
        sa.Column("session_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "client_user_audit",
        sa.Column("user_agent", sa.String(500), nullable=True),
    )
    op.add_column(
        "client_user_audit",
        sa.Column("action_type", sa.String(50), nullable=True),
    )

    op.create_index(
        "ix_client_audit_project_chain",
        "client_user_audit",
        ["project_id", "chain_index"],
    )
    op.create_index(
        "ix_client_audit_action_type",
        "client_user_audit",
        ["action_type"],
    )

    # GRANT INSERT/UPDATE para que el service pueda escribir nuevos rows
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON client_user_audit TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_index("ix_client_audit_action_type", table_name="client_user_audit")
    op.drop_index(
        "ix_client_audit_project_chain", table_name="client_user_audit",
    )
    op.drop_column("client_user_audit", "action_type")
    op.drop_column("client_user_audit", "user_agent")
    op.drop_column("client_user_audit", "session_id")
    op.drop_column("client_user_audit", "current_hash")
    op.drop_column("client_user_audit", "prev_hash")
    op.drop_column("client_user_audit", "chain_index")
    op.drop_column("client_user_audit", "project_id")
