"""M18 Communication + M23 Retainer Management.

M18:
- Extend status_reports: periodo_inicio/fin, contenido_jsonb, semaforo_rag,
  docx_path, pdf_path, estado, generado_at, revisado_at, abierto_at
- Create communication_plans (project_id unique + RLS)
- Create escalation_events (project_id + RLS)

M23:
- Extend retainer_contracts: project_id (FK+RLS), contract_id, perfil, estado,
  next_renewal_date, renewal_status, rag_status, horas_consumidas_total,
  horas_previstas_anual
- Extend retainer_activities: project_id (FK+RLS), titulo, descripcion,
  horas_estimadas, resultado, prioridad
- Create retainer_drift_events (project_id + RLS)

retainer_contracts mantiene RLS por client_id (existente) + añade policy
por project_id (tolerante a NULL para registros legacy).

Revision ID: e2b8f3c91a7d
Revises: d9e4a71b2c5f
Create Date: 2026-04-18 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e2b8f3c91a7d"
down_revision: Union[str, None] = "d9e4a71b2c5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═══════════════════════════════════════
    # M18 — extend status_reports
    # ═══════════════════════════════════════
    op.add_column("status_reports", sa.Column("periodo_inicio", sa.Date(), nullable=True))
    op.add_column("status_reports", sa.Column("periodo_fin", sa.Date(), nullable=True))
    op.add_column("status_reports", sa.Column("contenido_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("status_reports", sa.Column("semaforo_rag", sa.String(length=10), nullable=True))
    op.add_column("status_reports", sa.Column("docx_path", sa.String(length=500), nullable=True))
    op.add_column("status_reports", sa.Column("pdf_path", sa.String(length=500), nullable=True))
    op.add_column("status_reports", sa.Column("estado", sa.String(length=20), nullable=False, server_default="draft"))
    op.add_column("status_reports", sa.Column("generado_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("status_reports", sa.Column("revisado_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("status_reports", sa.Column("abierto_at", postgresql.TIMESTAMP(timezone=True), nullable=True))

    # M18 — communication_plans
    op.create_table(
        "communication_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("destinatarios", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("frecuencias", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("escalations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("activado_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", name="uq_communication_plan_project_id"),
    )
    op.create_index("ix_communication_plans_project_id", "communication_plans", ["project_id"])

    # M18 — escalation_events
    op.create_table(
        "escalation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("trigger", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("notificados", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("canal", sa.String(length=50), nullable=False),
        sa.Column("resuelto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resuelto_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("feed_item_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_escalation_events_project_id", "escalation_events", ["project_id"])

    # ═══════════════════════════════════════
    # M23 — extend retainer_contracts
    # ═══════════════════════════════════════
    op.add_column("retainer_contracts", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_retainer_contracts_project_id", "retainer_contracts", "projects",
        ["project_id"], ["id"],
    )
    op.add_column("retainer_contracts", sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_retainer_contracts_contract_id", "retainer_contracts", "contracts",
        ["contract_id"], ["id"],
    )
    op.add_column("retainer_contracts", sa.Column("perfil", sa.String(length=20), nullable=True, server_default="R_STD"))
    op.add_column("retainer_contracts", sa.Column("estado", sa.String(length=20), nullable=True, server_default="active"))
    op.add_column("retainer_contracts", sa.Column("next_renewal_date", sa.Date(), nullable=True))
    op.add_column("retainer_contracts", sa.Column("renewal_status", sa.String(length=30), nullable=True))
    op.add_column("retainer_contracts", sa.Column("rag_status", sa.String(length=10), nullable=True, server_default="green"))
    op.add_column("retainer_contracts", sa.Column("horas_consumidas_total", sa.Float(), nullable=True, server_default="0"))
    op.add_column("retainer_contracts", sa.Column("horas_previstas_anual", sa.Float(), nullable=True, server_default="40"))

    # M23 — extend retainer_activities
    op.add_column("retainer_activities", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_retainer_activities_project_id", "retainer_activities", "projects",
        ["project_id"], ["id"],
    )
    op.add_column("retainer_activities", sa.Column("titulo", sa.String(length=300), nullable=True))
    op.add_column("retainer_activities", sa.Column("descripcion", sa.Text(), nullable=True))
    op.add_column("retainer_activities", sa.Column("horas_estimadas", sa.Float(), nullable=True, server_default="0"))
    op.add_column("retainer_activities", sa.Column("resultado", sa.Text(), nullable=True))
    op.add_column("retainer_activities", sa.Column("prioridad", sa.String(length=10), nullable=True, server_default="normal"))

    # M23 — retainer_drift_events
    op.create_table(
        "retainer_drift_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("retainer_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("retainer_contracts.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dimension", sa.String(length=30), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("severidad", sa.String(length=10), nullable=False),
        sa.Column("impacto", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("resuelto_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_drift_events_retainer_id", "retainer_drift_events", ["retainer_contract_id"])
    op.create_index("ix_drift_events_project_id", "retainer_drift_events", ["project_id"])

    # ═══════════════════════════════════════
    # RLS — nuevas tablas project-scoped
    # ═══════════════════════════════════════
    for table in (
        "communication_plans",
        "escalation_events",
        "retainer_activities",
        "retainer_drift_events",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id() OR project_id IS NULL)"
        )

    # retainer_contracts: ya tiene policy client_isolation por client_id.
    # Añadir policy project_isolation adicional (RLS suma con OR entre policies).
    op.execute(
        "CREATE POLICY project_isolation ON retainer_contracts "
        "USING (project_id = current_project_id() OR project_id IS NULL)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON retainer_contracts")

    for table in (
        "retainer_drift_events",
        "retainer_activities",
        "escalation_events",
        "communication_plans",
    ):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_drift_events_project_id", table_name="retainer_drift_events")
    op.drop_index("ix_drift_events_retainer_id", table_name="retainer_drift_events")
    op.drop_table("retainer_drift_events")

    op.drop_column("retainer_activities", "prioridad")
    op.drop_column("retainer_activities", "resultado")
    op.drop_column("retainer_activities", "horas_estimadas")
    op.drop_column("retainer_activities", "descripcion")
    op.drop_column("retainer_activities", "titulo")
    op.drop_constraint("fk_retainer_activities_project_id", "retainer_activities", type_="foreignkey")
    op.drop_column("retainer_activities", "project_id")

    for col in (
        "horas_previstas_anual", "horas_consumidas_total", "rag_status",
        "renewal_status", "next_renewal_date", "estado", "perfil",
    ):
        op.drop_column("retainer_contracts", col)
    op.drop_constraint("fk_retainer_contracts_contract_id", "retainer_contracts", type_="foreignkey")
    op.drop_column("retainer_contracts", "contract_id")
    op.drop_constraint("fk_retainer_contracts_project_id", "retainer_contracts", type_="foreignkey")
    op.drop_column("retainer_contracts", "project_id")

    op.drop_index("ix_escalation_events_project_id", table_name="escalation_events")
    op.drop_table("escalation_events")

    op.drop_index("ix_communication_plans_project_id", table_name="communication_plans")
    op.drop_table("communication_plans")

    for col in (
        "abierto_at", "revisado_at", "generado_at", "estado", "pdf_path",
        "docx_path", "semaforo_rag", "contenido_jsonb", "periodo_fin", "periodo_inicio",
    ):
        op.drop_column("status_reports", col)
