"""ola_d_trusted_timestamps_004 · sellos de tiempo RFC 3161

feat/fulkro-100 Ola D · gap ALTA. Crea ``trusted_timestamps`` (append-only,
genérica) para guardar los sellos RFC 3161 de artefactos (firmas, evidencias…)
sin tocar las tablas inmutables que sella. RLS directa por project_id.

ADDITIVE · DB-safe (tabla nueva).

Revision ID: ola_d_trusted_timestamps_004
Revises: ola_d_magerit_economic_values_003
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

revision: str = "ola_d_trusted_timestamps_004"
down_revision: Union[str, None] = "ola_d_magerit_economic_values_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trusted_timestamps",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=40), nullable=False),
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("tsa_url", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("token", sa.LargeBinary(), nullable=True),
        sa.Column("gen_time", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index(
        "ix_trusted_timestamps_project_id",
        "trusted_timestamps", ["project_id"],
    )
    op.create_index(
        "ix_trusted_timestamps_artifact",
        "trusted_timestamps", ["artifact_type", "artifact_id"],
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON trusted_timestamps "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute("ALTER TABLE trusted_timestamps ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE trusted_timestamps FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON trusted_timestamps "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON trusted_timestamps")
    op.execute("ALTER TABLE trusted_timestamps DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_trusted_timestamps_artifact", table_name="trusted_timestamps",
    )
    op.drop_index(
        "ix_trusted_timestamps_project_id", table_name="trusted_timestamps",
    )
    op.drop_table("trusted_timestamps")
