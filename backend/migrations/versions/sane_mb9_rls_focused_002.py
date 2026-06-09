"""SAN-E MB-9 atom 9.3 · RLS focused apply to tenant-sensitive tables.

Q5.D cement post audit-driven [57/?]:
- 5 tables with project_id but NO RLS identified
- This migration applies RLS to 3 most critical for cliente isolation:
  · alert_queue (project-scoped alerts shown to cliente)
  · client_notifications (cliente-facing notifications)
  · connector_configs (per-project credentials)

Deferred for follow-up:
- llm_interaction_log · admin-only access already (NO cliente endpoint)
- oauth_state_tokens · transient session state (NO long-lived data)

Revision ID: sane_mb9_rls_focused_002
Revises: sane_mb9_branding_001
Create Date: 2026-05-12
"""
from alembic import op


revision = "sane_mb9_rls_focused_002"
down_revision = "sane_mb9_branding_001"
branch_labels = None
depends_on = None


TENANT_SENSITIVE_TABLES = [
    "alert_queue",
    "client_notifications",
    "connector_configs",
]


def upgrade() -> None:
    for table in TENANT_SENSITIVE_TABLES:
        op.execute(
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
        )
        op.execute(
            f"""
            CREATE POLICY {table}_project_isolation ON {table}
            FOR ALL TO fulkro_app
            USING (
                project_id::text = current_setting(
                    'app.current_project_id', true
                )
            )
            WITH CHECK (
                project_id::text = current_setting(
                    'app.current_project_id', true
                )
            )
            """,
        )
        # Note: fulkro_app already has CRUD grants on existing tables via
        # base migrations · explicit re-grant for safety post-RLS enable.
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO fulkro_app"
        )


def downgrade() -> None:
    for table in TENANT_SENSITIVE_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS {table}_project_isolation ON {table}"
        )
        op.execute(
            f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"
        )
