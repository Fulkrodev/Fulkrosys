"""san_e_mb3_cleanup_m21_drop_role_columns

ADR-013 v3 SAN-E.MB-3.cleanup commit 3/6 · drop multi-role columns
de client_users · single-user-RW model.

Backup BD pre-cleanup en progress/archive/client_users_pre_cleanup_2026-05-08.json
(8 users con roles legacy preservados antes de drop).

Production · pre K.0 (15-may-2026): no hay clientes productivos. Las 8
filas legacy de client_users mantienen email + auth + sessions intactas.
Pierden role / custom_role_description / scopes_jsonb (columns dropped).
Implicit migration: todos los users -> RW unico.

Revision ID: d7e9a3b5c1f4
Revises: c2d4f6a8b1e3
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "d7e9a3b5c1f4"
down_revision: Union[str, None] = "c2d4f6a8b1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop role + custom_role_description + scopes_jsonb columns."""
    # Drop index ix_client_users_role primero (CASCADE no aplica a indexes)
    op.execute("DROP INDEX IF EXISTS ix_client_users_role;")
    op.execute("ALTER TABLE client_users DROP COLUMN IF EXISTS role;")
    op.execute(
        "ALTER TABLE client_users DROP COLUMN IF EXISTS custom_role_description;"
    )
    op.execute("ALTER TABLE client_users DROP COLUMN IF EXISTS scopes_jsonb;")


def downgrade() -> None:
    """Recrea columns NULL · NO restaura datos legacy.

    Para restaurar datos pre-cleanup desde JSON archive:
    psql -c "UPDATE client_users SET role=...,scopes_jsonb=... WHERE id=...;"
    usando progress/archive/client_users_pre_cleanup_2026-05-08.json.
    """
    op.execute(
        "ALTER TABLE client_users "
        "ADD COLUMN IF NOT EXISTS role varchar(40) "
        "NOT NULL DEFAULT 'lectura_solo';"
    )
    op.execute(
        "ALTER TABLE client_users "
        "ADD COLUMN IF NOT EXISTS custom_role_description text;"
    )
    op.execute(
        "ALTER TABLE client_users "
        "ADD COLUMN IF NOT EXISTS scopes_jsonb jsonb;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_users_role "
        "ON client_users (role);"
    )
