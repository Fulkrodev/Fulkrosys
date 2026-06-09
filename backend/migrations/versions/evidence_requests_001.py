"""Sesión 3B-2B.8 CLUSTER 3 Phase 3A · Evidence request system explicit.

NEW table evidence_requests con workflow state machine canonical:
- pending_cliente → pending_review → approved | rejected | cancelled
- cliente upload links Evidence row · admin approve/reject con motivo claro
- audit trail completo cliente VE/SUBE · admin VALIDA con trazabilidad ENAC

Filosofía cliente-mínimo: cliente VE tarea + SUBE archivo · NO opera Evidence
vault directamente · MARK-NA si no aplica + motivo amigable. Marcos VALIDA o
RECHAZA con motivo claro · audit_log Sub-atom 5.A propagated cross transitions.

Reuses:
- emit_client_notification + SSE wire Phase 2D (DRY central · auto SSE + audit_log)
- Pattern #14 SSE + ClientNotification dual emit
- Evidence row FK (evidence_id) cuando cliente uploads

Revision ID: evidence_requests_001
Revises: cliente_continuidad_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "evidence_requests_001"
down_revision: Union[str, None] = "cliente_continuidad_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_requests",
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
            nullable=True,
        ),
        sa.Column("measure_code", sa.String(40), nullable=True),
        sa.Column(
            "control_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("tipo_documento", sa.String(100), nullable=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("plantilla_url", sa.String(500), nullable=True),
        sa.Column("deadline_date", sa.Date, nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'pending_cliente'"),
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
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
        # Resolution metadata
        sa.Column(
            "cliente_uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cliente_na_motivo", sa.Text, nullable=True),
        sa.Column(
            "admin_validated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "admin_validated_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("admin_rejection_motivo", sa.Text, nullable=True),
        sa.CheckConstraint(
            "status IN ('pending_cliente', 'pending_review', 'approved', "
            "'rejected', 'cancelled', 'marked_na')",
            name="ck_evidence_requests_status",
        ),
    )

    op.create_index(
        "ix_evidence_requests_project_id",
        "evidence_requests",
        ["project_id"],
    )
    op.create_index(
        "ix_evidence_requests_status",
        "evidence_requests",
        ["status"],
    )
    op.create_index(
        "ix_evidence_requests_client_user_id",
        "evidence_requests",
        ["client_user_id"],
        postgresql_where=sa.text("client_user_id IS NOT NULL"),
    )

    # RLS isolation per project (Sub-atom 5.A pattern)
    op.execute("ALTER TABLE evidence_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE evidence_requests FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY evidence_requests_isolation ON evidence_requests
          USING (project_id = current_project_id())
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON evidence_requests "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS evidence_requests_isolation ON evidence_requests"
    )
    op.drop_index(
        "ix_evidence_requests_client_user_id",
        table_name="evidence_requests",
    )
    op.drop_index(
        "ix_evidence_requests_status",
        table_name="evidence_requests",
    )
    op.drop_index(
        "ix_evidence_requests_project_id",
        table_name="evidence_requests",
    )
    op.drop_table("evidence_requests")
