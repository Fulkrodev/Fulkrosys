"""ola_d_compensatory_controls_002 · medidas compensatorias tipadas (Art. 8)

feat/fulkro-100 Ola D · gap ALTA. Crea ``compensatory_controls`` para estructurar
las medidas compensatorias (RD 311/2022 Art. 8) que hoy son texto libre en
``dda_entries.justificacion_no_aplica``. RLS directa por project_id (fail-closed).

ADDITIVE · DB-safe (tabla nueva). El valor 'compensada' del enum Aplicabilidad NO
requiere DDL: ``dda_entries.aplicabilidad`` es VARCHAR(20) sin CHECK.

Revision ID: ola_d_compensatory_controls_002
Revises: ola_d_continuity_test_executions_001
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

revision: str = "ola_d_compensatory_controls_002"
down_revision: Union[str, None] = "ola_d_continuity_test_executions_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compensatory_controls",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "dda_entry_id", UUID(as_uuid=True),
            sa.ForeignKey("dda_entries.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("measure_code", sa.String(length=30), nullable=False),
        sa.Column("motivo_no_aplica_directa", sa.Text(), nullable=False),
        sa.Column("control_compensatorio", sa.Text(), nullable=False),
        sa.Column("riesgo_residual", sa.Text(), nullable=True),
        sa.Column(
            "estado", sa.String(length=30),
            server_default="pendiente_aprobacion", nullable=False,
        ),
        sa.Column("aprobado_por", sa.String(length=255), nullable=True),
        sa.Column("fecha_aprobacion", sa.Date(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "project_id", "measure_code",
            name="uq_compensatory_project_measure",
        ),
        sa.CheckConstraint(
            "estado IN ('pendiente_aprobacion', 'aprobada', 'rechazada')",
            name="ck_compensatory_estado",
        ),
        sa.CheckConstraint(
            "(estado = 'pendiente_aprobacion') OR (aprobado_por IS NOT NULL)",
            name="ck_compensatory_approval_consistency",
        ),
    )
    op.create_index(
        "ix_compensatory_controls_project_id",
        "compensatory_controls", ["project_id"],
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON compensatory_controls "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute("ALTER TABLE compensatory_controls ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE compensatory_controls FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON compensatory_controls "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON compensatory_controls"
    )
    op.execute("ALTER TABLE compensatory_controls DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_compensatory_controls_project_id",
        table_name="compensatory_controls",
    )
    op.drop_table("compensatory_controls")
