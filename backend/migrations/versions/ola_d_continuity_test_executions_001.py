"""ola_d_continuity_test_executions_001 · op.cont.3 registro de pruebas continuidad

feat/fulkro-100 Ola D · gap ALTA. Crea ``continuity_test_executions`` para
registrar la EJECUCIÓN de las pruebas periódicas del plan de continuidad (medida
ENS op.cont.3 · RD 311/2022 Anexo II). Tabla con project_id directo → RLS directa
``project_id = current_project_id()`` (fail-closed · espejo del patrón de tablas
project-scoped). Bypass admin por ATRIBUTO de rol ``fulkro_app_bypassrls``.

ADDITIVE · DB-safe (tabla nueva · 0 filas previas).

Revision ID: ola_d_continuity_test_executions_001
Revises: r26_nc_audit_findings_001
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

revision: str = "ola_d_continuity_test_executions_001"
down_revision: Union[str, None] = "r26_nc_audit_findings_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "continuity_test_executions",
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
        sa.Column("fecha_prueba", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("escenario", sa.String(length=255), nullable=False),
        sa.Column("resultado", sa.String(length=30), nullable=False),
        sa.Column("hallazgos", sa.Text(), nullable=True),
        sa.Column("proxima_prueba_due", sa.Date(), nullable=True),
        sa.Column("evidencia_ref", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "resultado IN ('pass', 'parcial', 'fail')",
            name="ck_continuity_test_resultado",
        ),
    )
    op.create_index(
        "ix_continuity_test_executions_project_id",
        "continuity_test_executions", ["project_id"],
    )
    op.create_index(
        "ix_continuity_test_executions_fecha",
        "continuity_test_executions", ["project_id", "fecha_prueba"],
    )

    # RLS directa por project_id (fail-closed · bypass admin por atributo de rol).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON continuity_test_executions "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute(
        "ALTER TABLE continuity_test_executions ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE continuity_test_executions FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY project_isolation ON continuity_test_executions "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON continuity_test_executions"
    )
    op.execute(
        "ALTER TABLE continuity_test_executions DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_continuity_test_executions_fecha",
        table_name="continuity_test_executions",
    )
    op.drop_index(
        "ix_continuity_test_executions_project_id",
        table_name="continuity_test_executions",
    )
    op.drop_table("continuity_test_executions")
