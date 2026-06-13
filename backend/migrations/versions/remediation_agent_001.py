"""remediation_agent_001 · ADR-055 Fase 3 agente on-prem

Crea ``remediation_agents`` + ``remediation_agent_commands`` (RLS directa
project_id) + 2 funciones SECURITY DEFINER que resuelven el agente/enrollment por
token hash CRUZANDO RLS (el agente no tiene contexto de proyecto hasta resolverse;
el token ES la autenticación · patrón espejo de get_project_owner).

ADDITIVE · DB-safe (tablas nuevas 0 filas).

Revision ID: remediation_agent_001
Revises: remediation_engine_001
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision: str = "remediation_agent_001"
down_revision: Union[str, None] = "remediation_engine_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enable_project_rls(table: str) -> None:
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY project_isolation ON {table} "
        "USING (project_id = current_project_id())"
    )


def upgrade() -> None:
    # ── remediation_agents ──────────────────────────────────────────────
    op.create_table(
        "remediation_agents",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("client_id", UUID(as_uuid=True), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("enrollment_token_hash", sa.String(length=64), nullable=True),
        sa.Column("enrollment_expires_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("agent_pubkey_hex", sa.String(length=64), nullable=True),
        sa.Column("agent_token_hash", sa.String(length=64), nullable=True),
        sa.Column("agent_version", sa.String(length=40), nullable=True),
        sa.Column("capabilities", JSONB, nullable=True),
        sa.Column("enrolled_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'revoked')",
            name="ck_remediation_agents_status",
        ),
    )
    op.create_index(
        "ix_remediation_agents_project_status",
        "remediation_agents", ["project_id", "status"],
    )
    op.create_index(
        "ix_remediation_agents_token", "remediation_agents", ["agent_token_hash"],
    )
    op.create_index(
        "ix_remediation_agents_enroll",
        "remediation_agents", ["enrollment_token_hash"],
    )
    _enable_project_rls("remediation_agents")

    # ── remediation_agent_commands ──────────────────────────────────────
    op.create_table(
        "remediation_agent_commands",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "agent_id", UUID(as_uuid=True),
            sa.ForeignKey("remediation_agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id", UUID(as_uuid=True),
            sa.ForeignKey("remediation_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("playbook_id", sa.String(length=80), nullable=False),
        sa.Column("params", JSONB, nullable=True),
        sa.Column(
            "issued_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("server_signature", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("report_signature", sa.Text(), nullable=True),
        sa.Column("delivered_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reported_at", TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'delivered', 'reported')",
            name="ck_remediation_agent_cmds_status",
        ),
    )
    op.create_index(
        "ix_remediation_agent_cmds_agent",
        "remediation_agent_commands", ["agent_id", "status"],
    )
    op.create_index(
        "ix_remediation_agent_cmds_project",
        "remediation_agent_commands", ["project_id"],
    )
    _enable_project_rls("remediation_agent_commands")

    # ── SECURITY DEFINER resolvers (token → agente · cruzan RLS) ─────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_resolve_remediation_agent(p_token_hash text)
        RETURNS TABLE(agent_id uuid, project_id uuid, status text, agent_pubkey_hex text)
        LANGUAGE sql SECURITY DEFINER STABLE
        AS $$
          SELECT id, project_id, status, agent_pubkey_hex
          FROM remediation_agents
          WHERE agent_token_hash = p_token_hash AND deleted_at IS NULL
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_resolve_remediation_enrollment(p_token_hash text)
        RETURNS TABLE(agent_id uuid, project_id uuid, status text, expires_at timestamptz)
        LANGUAGE sql SECURITY DEFINER STABLE
        AS $$
          SELECT id, project_id, status, enrollment_expires_at
          FROM remediation_agents
          WHERE enrollment_token_hash = p_token_hash AND deleted_at IS NULL
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION fn_resolve_remediation_agent(text) "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION fn_resolve_remediation_enrollment(text) "
        "TO fulkro_app, fulkro_app_bypassrls"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_resolve_remediation_enrollment(text)")
    op.execute("DROP FUNCTION IF EXISTS fn_resolve_remediation_agent(text)")

    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON remediation_agent_commands"
    )
    op.execute(
        "ALTER TABLE remediation_agent_commands DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_remediation_agent_cmds_project",
        table_name="remediation_agent_commands",
    )
    op.drop_index(
        "ix_remediation_agent_cmds_agent", table_name="remediation_agent_commands",
    )
    op.drop_table("remediation_agent_commands")

    op.execute("DROP POLICY IF EXISTS project_isolation ON remediation_agents")
    op.execute("ALTER TABLE remediation_agents DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_remediation_agents_enroll", table_name="remediation_agents")
    op.drop_index("ix_remediation_agents_token", table_name="remediation_agents")
    op.drop_index(
        "ix_remediation_agents_project_status", table_name="remediation_agents",
    )
    op.drop_table("remediation_agents")
