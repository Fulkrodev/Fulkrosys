"""M10 Audit Simulation + M20 Workspace Extensions.

M10:
- Create audit_simulation_runs + audit_simulation_findings
- RLS policies by project_id

M20:
- Add project_id FK to workspace_files + videocall_sessions
- Extend collaborative_workspaces: nombre, config
- Extend workspace_files: carpeta, storage_path, tamano_bytes, version, estado
- Extend videocall_sessions: estado, solicitada_por, aceptada_at,
  duracion_minutos, livekit_room_name
- Add unique constraint on collaborative_workspaces.project_id (1:1 proyecto)
- Create workspace_feed_items + workspace_chat_messages
- RLS on workspace_files, videocall_sessions, workspace_feed_items,
  workspace_chat_messages (project_id)

Revision ID: d9e4a71b2c5f
Revises: c8a3f2e1d4b5
Create Date: 2026-04-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d9e4a71b2c5f"
down_revision: Union[str, None] = "c8a3f2e1d4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═══════════════════════════════════════
    # M10 — audit_simulation_runs
    # ═══════════════════════════════════════
    op.create_table(
        "audit_simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("categoria", sa.String(length=10), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("total_measures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("measures_evaluated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conformes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_conformes_mayores", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_conformes_menores", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observaciones", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_aplica", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_global", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nivel_madurez_global", sa.String(length=5), nullable=False, server_default="L0"),
        sa.Column("scores_por_familia", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("contradicciones_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("informe_path", sa.String(length=500), nullable=True),
        sa.Column("recomendacion", sa.String(length=50), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_audit_sim_runs_project_id", "audit_simulation_runs", ["project_id"])

    # M10 — audit_simulation_findings
    op.create_table(
        "audit_simulation_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_simulation_runs.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("measure_code", sa.String(length=20), nullable=False),
        sa.Column("measure_name", sa.String(length=300), nullable=False),
        sa.Column("measure_family", sa.String(length=20), nullable=False),
        sa.Column("pregunta_auditor", sa.Text(), nullable=False),
        sa.Column("criterio_aceptacion", sa.Text(), nullable=False),
        sa.Column("documento_esperado", sa.String(length=20), nullable=True),
        sa.Column("documento_encontrado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidencia_encontrada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidencia_vigente", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidencia_suficiente", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evaluacion", sa.String(length=30), nullable=False),
        sa.Column("nivel_madurez", sa.String(length=5), nullable=False, server_default="L0"),
        sa.Column("hallazgo_descripcion", sa.Text(), nullable=True),
        sa.Column("accion_requerida", sa.Text(), nullable=True),
        sa.Column("plazo_sugerido_dias", sa.Integer(), nullable=True),
        sa.Column("contradiccion_detectada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("contradiccion_detalle", sa.Text(), nullable=True),
        sa.Column("evidencia_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pentest_finding_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_audit_sim_findings_run_id", "audit_simulation_findings", ["run_id"])
    op.create_index("ix_audit_sim_findings_project_id", "audit_simulation_findings", ["project_id"])
    op.create_index("ix_audit_sim_findings_measure_code", "audit_simulation_findings", ["measure_code"])

    # ═══════════════════════════════════════
    # M20 — extend collaborative_workspaces
    # ═══════════════════════════════════════
    op.add_column("collaborative_workspaces", sa.Column("nombre", sa.String(length=200), nullable=True))
    op.add_column("collaborative_workspaces", sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_unique_constraint("uq_workspace_project_id", "collaborative_workspaces", ["project_id"])

    # M20 — extend workspace_files
    op.add_column("workspace_files", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workspace_files_project_id", "workspace_files", "projects",
        ["project_id"], ["id"],
    )
    op.add_column("workspace_files", sa.Column("carpeta", sa.String(length=500), nullable=True, server_default="/"))
    op.add_column("workspace_files", sa.Column("storage_path", sa.String(length=500), nullable=True))
    op.add_column("workspace_files", sa.Column("tamano_bytes", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("workspace_files", sa.Column("version", sa.Integer(), nullable=True, server_default="1"))
    op.add_column("workspace_files", sa.Column("estado", sa.String(length=20), nullable=True, server_default="active"))
    # Widen nombre column: 255 → 300
    op.alter_column("workspace_files", "nombre", type_=sa.String(length=300), existing_type=sa.String(length=255), existing_nullable=False)

    # M20 — extend videocall_sessions
    op.add_column("videocall_sessions", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_videocall_sessions_project_id", "videocall_sessions", "projects",
        ["project_id"], ["id"],
    )
    op.add_column("videocall_sessions", sa.Column("estado", sa.String(length=20), nullable=True, server_default="solicitada"))
    op.add_column("videocall_sessions", sa.Column("solicitada_por", sa.String(length=100), nullable=True))
    op.add_column("videocall_sessions", sa.Column("aceptada_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("videocall_sessions", sa.Column("duracion_minutos", sa.Integer(), nullable=True))
    op.add_column("videocall_sessions", sa.Column("livekit_room_name", sa.String(length=200), nullable=True))

    # M20 — workspace_feed_items
    op.create_table(
        "workspace_feed_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collaborative_workspaces.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("item_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("autor", sa.String(length=100), nullable=False, server_default="plataforma"),
        sa.Column("leido", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("leido_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_feed_items_workspace_id", "workspace_feed_items", ["workspace_id"])
    op.create_index("ix_feed_items_project_id", "workspace_feed_items", ["project_id"])
    op.create_index("ix_feed_items_tipo", "workspace_feed_items", ["tipo"])

    # M20 — workspace_chat_messages
    op.create_table(
        "workspace_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collaborative_workspaces.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("autor", sa.String(length=200), nullable=False),
        sa.Column("autor_tipo", sa.String(length=20), nullable=False, server_default="marcos"),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("adjunto_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("respondiendo_a", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_chat_messages_workspace_id", "workspace_chat_messages", ["workspace_id"])
    op.create_index("ix_chat_messages_project_id", "workspace_chat_messages", ["project_id"])

    # ═══════════════════════════════════════
    # RLS — tablas project-scoped
    # ═══════════════════════════════════════
    for table in (
        "audit_simulation_runs",
        "audit_simulation_findings",
        "workspace_files",
        "videocall_sessions",
        "workspace_feed_items",
        "workspace_chat_messages",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id() OR project_id IS NULL)"
        )


def downgrade() -> None:
    for table in (
        "workspace_chat_messages",
        "workspace_feed_items",
        "videocall_sessions",
        "workspace_files",
        "audit_simulation_findings",
        "audit_simulation_runs",
    ):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_chat_messages_project_id", table_name="workspace_chat_messages")
    op.drop_index("ix_chat_messages_workspace_id", table_name="workspace_chat_messages")
    op.drop_table("workspace_chat_messages")

    op.drop_index("ix_feed_items_tipo", table_name="workspace_feed_items")
    op.drop_index("ix_feed_items_project_id", table_name="workspace_feed_items")
    op.drop_index("ix_feed_items_workspace_id", table_name="workspace_feed_items")
    op.drop_table("workspace_feed_items")

    op.drop_column("videocall_sessions", "livekit_room_name")
    op.drop_column("videocall_sessions", "duracion_minutos")
    op.drop_column("videocall_sessions", "aceptada_at")
    op.drop_column("videocall_sessions", "solicitada_por")
    op.drop_column("videocall_sessions", "estado")
    op.drop_constraint("fk_videocall_sessions_project_id", "videocall_sessions", type_="foreignkey")
    op.drop_column("videocall_sessions", "project_id")

    op.alter_column("workspace_files", "nombre", type_=sa.String(length=255), existing_type=sa.String(length=300), existing_nullable=False)
    op.drop_column("workspace_files", "estado")
    op.drop_column("workspace_files", "version")
    op.drop_column("workspace_files", "tamano_bytes")
    op.drop_column("workspace_files", "storage_path")
    op.drop_column("workspace_files", "carpeta")
    op.drop_constraint("fk_workspace_files_project_id", "workspace_files", type_="foreignkey")
    op.drop_column("workspace_files", "project_id")

    op.drop_constraint("uq_workspace_project_id", "collaborative_workspaces", type_="unique")
    op.drop_column("collaborative_workspaces", "config")
    op.drop_column("collaborative_workspaces", "nombre")

    op.drop_index("ix_audit_sim_findings_measure_code", table_name="audit_simulation_findings")
    op.drop_index("ix_audit_sim_findings_project_id", table_name="audit_simulation_findings")
    op.drop_index("ix_audit_sim_findings_run_id", table_name="audit_simulation_findings")
    op.drop_table("audit_simulation_findings")

    op.drop_index("ix_audit_sim_runs_project_id", table_name="audit_simulation_runs")
    op.drop_table("audit_simulation_runs")
