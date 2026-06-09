"""m27: conformity_state_snapshots table for route history + external exports.

Revision ID: a1b2c3d4e5f6
Revises: f4a8c7b1d2e3
Create Date: 2026-04-29 19:30:00.000000

Sub-fase 5.5.F.0.G — refactor m27 api.py de in-memory dicts a DB-backed.

Las 13 tablas conformity_lifecycle existing pre-S11 (migración
e3f7a5b2d412) cubren el grueso de estructuras: routes, submissions,
basic_declarations, pce_overlays, renewals, material_changes,
recategorizations, extraordinary_audits, role_topologies, etc.

PERO _ROUTE_HISTORY (timeline transitions estado) y _EXPORTS
(external system exports) NO tienen modelo dedicado. Esta migración
añade UNA tabla genérica polimórfica que persiste ambos:

  - snapshot_type='route_transition' → metadata={from, to, reason, at}
  - snapshot_type='external_export'  → metadata={tool, params, artifact,
                                                  proof_uploaded, proof_reference}

Razón polimórfica: ambos tipos tienen shape común (project_id +
payload arbitrario JSONB + timestamp). Evita 2 tablas dedicadas por
casos con bajo volumen y schema casi-idéntico. Pattern coherente
con audit_log entries.

Política TODO-DB-DRIFT-001: revision SIN --autogenerate.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f4a8c7b1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conformity_state_snapshots",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_type", sa.String(40), nullable=False),
        # route_transition | external_export | other
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index(
        "ix_conformity_state_snapshots_project_type",
        "conformity_state_snapshots",
        ["project_id", "snapshot_type", "created_at"],
    )

    # RLS USING (true) permissive (M27 admin-only por RBAC require_owner
    # router-level — pattern coherente con M30 5.5.A).
    op.execute(
        "ALTER TABLE conformity_state_snapshots ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE conformity_state_snapshots FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY admin_all ON conformity_state_snapshots "
        "USING (true) WITH CHECK (true)"
    )

    # Audit trigger reusa fn_audit_track (12 tablas + admin_settings + M30).
    op.execute(
        "CREATE TRIGGER tg_audit_conformity_state_snapshots "
        "AFTER INSERT OR UPDATE OR DELETE ON conformity_state_snapshots "
        "FOR EACH ROW EXECUTE FUNCTION fn_audit_track();"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_conformity_state_snapshots "
        "ON conformity_state_snapshots"
    )
    op.execute(
        "DROP POLICY IF EXISTS admin_all ON conformity_state_snapshots"
    )
    op.execute(
        "ALTER TABLE conformity_state_snapshots DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_conformity_state_snapshots_project_type",
        table_name="conformity_state_snapshots",
    )
    op.drop_table("conformity_state_snapshots")
