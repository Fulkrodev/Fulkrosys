"""e155_scope_model_001 · R05 · modelo de scope estructurado para E-155

Documento de Alcance del SGSI (E-155 · CCN-STIC 805/809). Hasta ahora el alcance
se renderizaba con placeholders ("PENDIENTE REVISIÓN CONSULTOR") porque no había
modelo estructurado. Esta migración (ADDITIVE · DB-safe) lo crea:

  * ``services.tipo``  ∈ {finalista, instrumental}  (CCN-STIC 803 · NULLABLE)
  * ``system_sites``   · sedes físicas / regiones cloud en alcance (ALTA exige
                         ubicaciones reales con dirección + país)
  * ``scope_exclusions`` · exclusiones justificadas del alcance (E-155 §4)

Las 2 tablas nuevas heredan el aislamiento por proyecto del padre ``systems``
(mirror EXACTO de la policy ``project_isolation`` de ``services`` —migración
33cef115cdf5—), en variante fail-closed (USING + WITH CHECK, sin OR...IS NULL
permisivo). Si no hay contexto de proyecto, ``current_project_id()`` devuelve
NULL → EXISTS falso → 0 filas. El bypass admin lo aporta el ATRIBUTO de rol
``fulkro_app_bypassrls`` (BYPASSRLS), no la policy; ``fulkro_migrate`` (owner,
BYPASSRLS) tampoco se ve afectado por FORCE.

Estilo de tablas mirror de ``1350b2466202_initial_schema_69_tables`` (FullMixin:
id uuid gen_random_uuid · created_at now() NOT NULL · updated_at/deleted_at
nullable · FK sin nombre explícito).

Revision ID: e155_scope_model_001
Revises: rls_canonical_policies_002
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e155_scope_model_001"
down_revision: Union[str, None] = "rls_canonical_policies_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _scope_child_rls(table: str) -> None:
    """ENABLE+FORCE RLS + policy ``project_isolation`` vía ``systems`` (fail-closed).

    Mirror de la policy de ``services`` (child-via-parent) endurecida con
    WITH CHECK para impedir además INSERT/UPDATE con system_id de otro tenant.
    """
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY project_isolation ON {table} "
        f"USING (EXISTS (SELECT 1 FROM systems s "
        f"WHERE s.id = {table}.system_id "
        f"AND s.project_id = current_project_id())) "
        f"WITH CHECK (EXISTS (SELECT 1 FROM systems s "
        f"WHERE s.id = {table}.system_id "
        f"AND s.project_id = current_project_id()))"
    )


def upgrade() -> None:
    # ── services.tipo (finalista | instrumental · CCN-STIC 803) ──
    op.add_column(
        "services",
        sa.Column("tipo", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "ck_services_tipo",
        "services",
        "tipo IS NULL OR tipo IN ('finalista', 'instrumental')",
    )

    # ── system_sites (sedes físicas / regiones cloud en alcance · E-155 §3.3) ──
    op.create_table(
        "system_sites",
        sa.Column("system_id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("pais", sa.String(length=100), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "id", sa.UUID(),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "tipo IS NULL OR tipo IN ('sede_fisica', 'region_cloud')",
            name="ck_system_sites_tipo",
        ),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    _scope_child_rls("system_sites")

    # ── scope_exclusions (exclusiones justificadas · E-155 §4) ──
    op.create_table(
        "scope_exclusions",
        sa.Column("system_id", sa.UUID(), nullable=False),
        sa.Column("elemento", sa.String(length=255), nullable=False),
        sa.Column("justificacion", sa.Text(), nullable=True),
        sa.Column(
            "id", sa.UUID(),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    _scope_child_rls("scope_exclusions")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON scope_exclusions")
    op.drop_table("scope_exclusions")
    op.execute("DROP POLICY IF EXISTS project_isolation ON system_sites")
    op.drop_table("system_sites")
    op.drop_constraint("ck_services_tipo", "services", type_="check")
    op.drop_column("services", "tipo")
