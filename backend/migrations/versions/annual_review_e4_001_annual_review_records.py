"""#4 Ola8: annual_review_records (revision anual AR/DdA) + dda_entries link

Revision ID: annual_review_e4_001
Revises: categoria_heredada_e5_001
Create Date: 2026-06-05

Registro de auditoria del ciclo de revision anual del Analisis de Riesgos /
Declaracion de Aplicabilidad (Fase 8 mantenimiento · CCN-STIC 808). Cada
revision snapshotea el estado vigente de las 73 medidas, bumpa la version de
las dda_entries y exige reaprobacion de Direccion.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "annual_review_e4_001"
down_revision: Union[str, None] = "categoria_heredada_e5_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annual_review_records",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("dda_version_from", sa.Integer(), nullable=True),
        sa.Column("dda_version_to", sa.Integer(), nullable=True),
        sa.Column(
            "estado", sa.String(50), nullable=False, server_default="pending",
        ),  # pending | approved | rejected
        sa.Column(
            "completion_snapshot", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("aprobado_por", sa.String(255), nullable=True),
        sa.Column("fecha_aprobacion", sa.Date(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_annual_review_records_project_id",
        "annual_review_records", ["project_id"],
    )
    op.create_index(
        "ix_annual_review_records_estado",
        "annual_review_records", ["estado"],
    )

    # Trazabilidad per-entrada: que DdA se reviso en que aniversario.
    op.add_column(
        "dda_entries",
        sa.Column(
            "annual_review_record_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("annual_review_records.id"), nullable=True,
        ),
    )

    # RLS project_isolation (ADR-013) + GRANT fulkro_app (regla 9).
    op.execute("ALTER TABLE annual_review_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE annual_review_records FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON annual_review_records "
        "USING (project_id = current_project_id())"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON annual_review_records "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON annual_review_records")
    op.execute("ALTER TABLE annual_review_records DISABLE ROW LEVEL SECURITY")
    op.drop_column("dda_entries", "annual_review_record_id")
    op.drop_index(
        "ix_annual_review_records_estado", table_name="annual_review_records",
    )
    op.drop_index(
        "ix_annual_review_records_project_id", table_name="annual_review_records",
    )
    op.drop_table("annual_review_records")
