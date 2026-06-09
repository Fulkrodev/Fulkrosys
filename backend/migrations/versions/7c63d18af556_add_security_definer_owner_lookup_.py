"""add_security_definer_owner_lookup_functions

Revision ID: 7c63d18af556
Revises: 3adc8d40b5ea
Create Date: 2026-04-13 01:32:51.319060
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c63d18af556'
down_revision: Union[str, None] = '3adc8d40b5ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SECURITY DEFINER functions to resolve the RLS chicken-and-egg problem.
    # Endpoints need to read projects/systems/magerit_analysis to find the
    # client_id BEFORE they can set tenant context, but RLS blocks that read.
    # These functions run as the table owner (fulkro superuser) bypassing RLS,
    # exposing ONLY the client_id needed for set_tenant_context().

    op.execute("""
        CREATE OR REPLACE FUNCTION get_project_owner(p_project_id UUID)
        RETURNS UUID
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
            SELECT client_id FROM projects WHERE id = p_project_id;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION get_system_owner(p_system_id UUID)
        RETURNS TABLE(client_id UUID, project_id UUID)
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
            SELECT p.client_id, s.project_id
            FROM systems s
            JOIN projects p ON p.id = s.project_id
            WHERE s.id = p_system_id;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION get_magerit_analysis_owner(p_analysis_id UUID)
        RETURNS TABLE(client_id UUID, project_id UUID)
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
            SELECT p.client_id, a.project_id
            FROM magerit_analysis a
            JOIN projects p ON p.id = a.project_id
            WHERE a.id = p_analysis_id;
        $$;
    """)

    # Grant execute to the app user
    op.execute("GRANT EXECUTE ON FUNCTION get_project_owner(UUID) TO fulkro_app")
    op.execute("GRANT EXECUTE ON FUNCTION get_system_owner(UUID) TO fulkro_app")
    op.execute("GRANT EXECUTE ON FUNCTION get_magerit_analysis_owner(UUID) TO fulkro_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_magerit_analysis_owner(UUID)")
    op.execute("DROP FUNCTION IF EXISTS get_system_owner(UUID)")
    op.execute("DROP FUNCTION IF EXISTS get_project_owner(UUID)")
