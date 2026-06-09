"""m28: change governance — extend changes + change_topologies table.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-29 19:50:00.000000

Sub-fase 5.5.F.0.H — refactor m28 api.py de in-memory dicts a DB-backed.

m28 motor previamente usaba 4 dicts in-memory:
  _CHANGES, _RECATEGORIZATIONS, _EXTRAORDINARY_AUDITS, _TOPOLOGIES.

Esta migración:

1. ``ALTER TABLE changes ADD COLUMN metadata_jsonb JSONB``
   Tabla ``changes`` existing en ``backend/app/models/operations.py``
   con shape básico (project_id, descripcion, solicitante, aprobado_cab,
   fecha_implementacion, resultado). _CHANGES dict m28 incluye además
   ``state``, ``assessment`` (impact_vector + materiality_score +
   materiality_level), ``proposed_date``, ``requested_by``. Persiste
   estos campos extra como JSONB sin migración disruptiva del schema.

2. ``CREATE TABLE change_topologies``
   Patrón topología roles ENS (5 patterns: startup_unipersonal,
   pyme_basica/media, empresa_grande, admin_publica). Tabla nueva
   dedicada para reemplazar _TOPOLOGIES dict.

3. _RECATEGORIZATIONS y _EXTRAORDINARY_AUDITS m28 → reuso cross-motor
   m27.recategorizations + m27.extraordinary_audits (formalizado
   ADR-023). NO requiere migración nueva.

Política TODO-DB-DRIFT-001: revision SIN --autogenerate.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend changes with metadata_jsonb
    op.add_column(
        "changes",
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # 2. Create change_topologies table
    op.create_table(
        "change_topologies",
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
        sa.Column("pattern_id", sa.String(40), nullable=False),
        sa.Column(
            "detail_jsonb", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "requires_memo", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_change_topologies_project",
        "change_topologies", ["project_id"],
    )

    # RLS USING (true) admin-only (m28 admin-only por require_owner).
    op.execute(
        "ALTER TABLE change_topologies ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE change_topologies FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY admin_all ON change_topologies "
        "USING (true) WITH CHECK (true)"
    )

    # Audit triggers — fn_audit_track existing.
    op.execute(
        "CREATE TRIGGER tg_audit_change_topologies "
        "AFTER INSERT OR UPDATE OR DELETE ON change_topologies "
        "FOR EACH ROW EXECUTE FUNCTION fn_audit_track();"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_change_topologies ON change_topologies"
    )
    op.execute(
        "DROP POLICY IF EXISTS admin_all ON change_topologies"
    )
    op.execute(
        "ALTER TABLE change_topologies DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_change_topologies_project", table_name="change_topologies",
    )
    op.drop_table("change_topologies")

    op.drop_column("changes", "metadata_jsonb")
