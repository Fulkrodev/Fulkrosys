"""Add RLS policies for tenant isolation.

Per v2.1 Parte 4.3: RLS on all tables with client_id or project_id.
33 policies covering 33 tables for complete tenant virtual isolation.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "e41cd7163c02"
down_revision: Union[str, None] = "1350b2466202"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables with project_id isolation
PROJECT_TABLES = [
    "audit_sessions", "changes", "collaborative_workspaces",
    "committee_meetings", "controls", "dda_entries",
    "discovered_assets", "discovered_identities", "documents",
    "evidence", "findings", "incidents", "magic_links",
    "nominations", "obligations", "onboarding_sessions",
    "pentest_runs", "procedures", "project_exports",
    "project_lifecycle_states", "project_plans", "project_risks",
    "status_reports", "systems", "training_records", "vendors",
    "vulnerabilities", "archived_projects",
]

# Tables with client_id isolation
CLIENT_TABLES = [
    "client_dashboard_state", "client_workspaces",
    "invoices", "projects", "retainer_contracts",
]


def upgrade() -> None:
    for table in PROJECT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY project_isolation ON {table} USING (project_id = current_project_id())")

    for table in CLIENT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY client_isolation ON {table} USING (client_id = current_client_id())")


def downgrade() -> None:
    for table in PROJECT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in CLIENT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS client_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
