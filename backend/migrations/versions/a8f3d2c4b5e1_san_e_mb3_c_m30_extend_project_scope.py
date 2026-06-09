"""san_e_mb3_c_m30_extend_project_scope

ADR-046 v3 SAN-E.MB-3.C: extiende M30 client_contacts con dimension project
para soportar constraint v3 "1 contacto con portal_access per project".

Decision: Opcion C (extender · NO crear tabla nueva). Backward compat ·
contactos historicos siguen con project_id NULL.

Revision ID: a8f3d2c4b5e1
Revises: f4b2c8d1e7a3
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a8f3d2c4b5e1"
down_revision: Union[str, None] = "f4b2c8d1e7a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ADD COLUMN project_id + index + partial UNIQUE constraint v3."""
    op.execute(
        "ALTER TABLE client_contacts "
        "ADD COLUMN IF NOT EXISTS project_id uuid "
        "REFERENCES projects(id) ON DELETE CASCADE"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_contacts_project "
        "ON client_contacts (project_id) WHERE project_id IS NOT NULL"
    )
    # Constraint v3 implementacion DB: 1 contact con has_portal_access per project.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_client_contacts_one_portal_per_project "
        "ON client_contacts (project_id) "
        "WHERE has_portal_access = true "
        "  AND project_id IS NOT NULL "
        "  AND deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_client_contacts_one_portal_per_project")
    op.execute("DROP INDEX IF EXISTS ix_client_contacts_project")
    op.execute("ALTER TABLE client_contacts DROP COLUMN IF EXISTS project_id")
