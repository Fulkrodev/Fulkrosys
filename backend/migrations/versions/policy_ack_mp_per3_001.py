"""policy_ack_mp_per3_001 · R14 parte 2 · acuse de recibo de normativa por empleado

Materializa la evidencia de la medida mp.per.3 (Concienciación · PSI §11.b): el
registro per-empleado de que ha recibido y aceptado las normativas de seguridad
(identidad + fecha + versión del documento). El auditor ENAC lo exige como
prueba de la concienciación del personal.

ADDITIVE · DB-safe (tabla nueva, 0 filas). Project-scoped: RLS por
``project_id``/``client_id`` en variante fail-closed (USING + WITH CHECK ·
ambas columnas NOT NULL ⇒ sin contexto, ``current_*_id()`` = NULL ⇒ 0 filas).
El bypass admin lo aporta el ATRIBUTO de rol ``fulkro_app_bypassrls``
(BYPASSRLS), no una policy permisiva (lección del P0 FASE 0). Estilo de tabla
mirror de ``e155_scope_model_001`` (FullMixin).

Revision ID: policy_ack_mp_per3_001
Revises: fase0_rls_leak_fix_001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "policy_ack_mp_per3_001"
down_revision: Union[str, None] = "fase0_rls_leak_fix_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policy_acknowledgments",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("documento_codigo", sa.String(length=20), nullable=False),
        sa.Column(
            "documento_version", sa.String(length=20),
            server_default=sa.text("'1.0'"), nullable=False,
        ),
        sa.Column("empleado_nombre", sa.String(length=255), nullable=False),
        sa.Column("empleado_identidad", sa.String(length=255), nullable=True),
        sa.Column("empleado_departamento", sa.String(length=255), nullable=True),
        sa.Column("fecha_acuse", sa.Date(), nullable=False),
        sa.Column("medio", sa.String(length=40), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "id", sa.UUID(),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_acknowledgments_project_id",
        "policy_acknowledgments", ["project_id"],
    )
    op.create_index(
        "ix_policy_acknowledgments_client_id",
        "policy_acknowledgments", ["client_id"],
    )
    op.execute("ALTER TABLE policy_acknowledgments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE policy_acknowledgments FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON policy_acknowledgments "
        "USING (project_id = current_project_id() "
        "OR client_id = current_client_id()) "
        "WITH CHECK (project_id = current_project_id() "
        "OR client_id = current_client_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON policy_acknowledgments")
    op.drop_index(
        "ix_policy_acknowledgments_client_id", table_name="policy_acknowledgments",
    )
    op.drop_index(
        "ix_policy_acknowledgments_project_id", table_name="policy_acknowledgments",
    )
    op.drop_table("policy_acknowledgments")
