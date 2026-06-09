"""Sesión 3B-2B.8 CLUSTER 2 Phase 2F · cliente continuidad questionnaire+approve.

Filosofía cliente-mínimo: cliente RECIBE drafts Marcos preparados (BIA + DRP)
y APROVA/COMENTA binding decision · NO creator mode técnico ENS.

Tables NEW (REFRAMED scope ALTA gaps):
1. cliente_continuidad_input · 1 row per project (UNIQUE(project_id) upsert)
   - questionnaire raw input cliente · RTO/RPO tolerancia · procesos críticos
   - daily impact estimate + activos core + notas libres
2. cliente_continuidad_approval · audit trail approval/comments per draft
   - artifact_type 'bia' | 'drp' + draft_id + action approved/rejected/comment
   - feedback text + project_id + client_user_id

Both tables RLS isolated per project (Sub-atom 5.A 3-way pattern · backend
emit propagates project_id explicit · cliente endpoints _set_project_rls).

Backend MVP scope · cliente UI deferred CLUSTER 6 chronological navigation
backbone (architecturally coherent · per-phase task curation R29).

Revision ID: cliente_continuidad_001
Revises: auditor_clarification_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cliente_continuidad_001"
down_revision: Union[str, None] = "auditor_clarification_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Table 1 · cliente_continuidad_input (questionnaire upsert) ───
    op.create_table(
        "cliente_continuidad_input",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "submitted_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Questionnaire mínimo cliente fields (friendly R29)
        sa.Column("procesos_criticos", postgresql.JSONB, nullable=True),
        sa.Column("rto_horas_tolerancia", sa.Integer, nullable=True),
        sa.Column("rpo_horas_tolerancia", sa.Integer, nullable=True),
        sa.Column(
            "impacto_diario_eur",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column("activos_core", postgresql.JSONB, nullable=True),
        sa.Column("notas_cliente", sa.Text, nullable=True),
        sa.Column(
            "completed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint(
            "project_id", name="uq_cliente_continuidad_input_project",
        ),
    )

    op.create_index(
        "ix_cliente_continuidad_input_client_user_id",
        "cliente_continuidad_input",
        ["client_user_id"],
    )

    # RLS isolation per project
    op.execute(
        "ALTER TABLE cliente_continuidad_input ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE cliente_continuidad_input FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY cliente_continuidad_input_isolation
          ON cliente_continuidad_input
          USING (project_id = current_project_id())
        """
    )

    # GRANT runtime role · RLS enforced (default ACL fails fulkro_migrate-created
    # tables · explicit grant pattern Sub-atom 5.A established)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON cliente_continuidad_input "
        "TO fulkro_app"
    )

    # ─── Table 2 · cliente_continuidad_approval (audit trail) ───
    op.create_table(
        "cliente_continuidad_approval",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "artifact_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("comment_text", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_type IN ('bia', 'drp')",
            name="ck_cliente_continuidad_approval_type",
        ),
        sa.CheckConstraint(
            "action IN ('approved', 'rejected', 'comment')",
            name="ck_cliente_continuidad_approval_action",
        ),
    )

    op.create_index(
        "ix_cliente_continuidad_approval_project_id",
        "cliente_continuidad_approval",
        ["project_id"],
    )

    op.execute(
        "ALTER TABLE cliente_continuidad_approval ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE cliente_continuidad_approval FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY cliente_continuidad_approval_isolation
          ON cliente_continuidad_approval
          USING (project_id = current_project_id())
        """
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON cliente_continuidad_approval "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS cliente_continuidad_approval_isolation "
        "ON cliente_continuidad_approval"
    )
    op.drop_index(
        "ix_cliente_continuidad_approval_project_id",
        table_name="cliente_continuidad_approval",
    )
    op.drop_table("cliente_continuidad_approval")

    op.execute(
        "DROP POLICY IF EXISTS cliente_continuidad_input_isolation "
        "ON cliente_continuidad_input"
    )
    op.drop_index(
        "ix_cliente_continuidad_input_client_user_id",
        table_name="cliente_continuidad_input",
    )
    op.drop_table("cliente_continuidad_input")
