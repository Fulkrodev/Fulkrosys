"""C4 - M21 Diagnosis: stakeholders + business_processes + legal_obligations.

Tres tablas nucleares del motor diagnosis (spec M21).

Revision ID: b5d2a81f4e93
Revises: a3b9c7e5f2d1
Create Date: 2026-04-19 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b5d2a81f4e93"
down_revision: Union[str, None] = "a3b9c7e5f2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMMON_COLS = lambda: [
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
]


def upgrade() -> None:
    # stakeholders
    op.create_table(
        "stakeholders",
        *COMMON_COLS(),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("cargo", sa.String(length=200), nullable=True),
        sa.Column("departamento", sa.String(length=200), nullable=True),
        sa.Column("poder", sa.Integer(), nullable=True),
        sa.Column("interes", sa.Integer(), nullable=True),
        sa.Column("actitud", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("relaciones", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notas_confidenciales", sa.Text(), nullable=True),
    )
    op.create_index("ix_stakeholders_project_id", "stakeholders", ["project_id"])

    # business_processes
    op.create_table(
        "business_processes",
        *COMMON_COLS(),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("criticidad", sa.String(length=20), nullable=True),
        sa.Column("propietario", sa.String(length=200), nullable=True),
        sa.Column("dependencias", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sistemas_involucrados", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bpmn_mermaid", sa.Text(), nullable=True),
        sa.Column("rto_horas", sa.Integer(), nullable=True),
        sa.Column("rpo_horas", sa.Integer(), nullable=True),
    )
    op.create_index("ix_business_processes_project_id", "business_processes", ["project_id"])

    # legal_obligations
    op.create_table(
        "legal_obligations",
        *COMMON_COLS(),
        sa.Column("normativa", sa.String(length=200), nullable=False),
        sa.Column("articulo", sa.String(length=100), nullable=True),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("impacto_ens", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=30), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("measure_codes_relacionadas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_legal_obligations_project_id", "legal_obligations", ["project_id"])

    # RLS
    for table in ("stakeholders", "business_processes", "legal_obligations"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id() OR project_id IS NULL)"
        )


def downgrade() -> None:
    for table in ("legal_obligations", "business_processes", "stakeholders"):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_table(table)
