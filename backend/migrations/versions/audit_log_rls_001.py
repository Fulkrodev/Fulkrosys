"""Sub-atom 5.A · audit_log RLS hardening (Sesión 3B-2B.6 inline insert pre-CLUSTER 2).

Empirical correction Phase 1.5 isolation audit finding B: audit_log table existed
sin project_id/client_id columns + sin RLS. Esta migración:

1. ADD nullable project_id + client_id columns (additive · backward-compat)
2. ADD indexes para hot-path queries (auditor portal CLUSTER 2 Phase 7)
3. ENABLE + FORCE RLS · policy 3-way OR clause:
     project_id = current_project_id()
     OR client_id = current_client_id()
     OR (project_id IS NULL AND client_id IS NULL)  -- legacy + system events

NOT touched (preserve invariants):
- fn_audit_log_hash_chain (BEFORE INSERT · hash chain integrity preserved)
- fn_audit_log_immutable (UPDATE/DELETE raise · R6 inviolable)
- fn_audit_track (existing 13 tracked tables emit rows · sin project_id by design ·
  matched by 'project_id IS NULL AND client_id IS NULL' clause)

NEW emit sites desde CLUSTER 2 auditor portal Phase 7 fijarán project_id explícito
para auditor_view_dossier · auditor_download_zip · etc · enforce isolation.

Backfill historical rows: NO se intenta · INSERT-only audit_log → historical
permanece project_id NULL · cobertura policy `IS NULL AND IS NULL` clause.

Revision ID: audit_log_rls_001
Revises: audit_marked_event_type_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "audit_log_rls_001"
down_revision: Union[str, None] = "audit_marked_event_type_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add tenant scoping columns (nullable · additive)
    op.add_column(
        "audit_log",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "audit_log",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 2. Indexes para hot-path queries
    op.create_index(
        "ix_audit_log_project_id",
        "audit_log",
        ["project_id"],
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_log_client_id",
        "audit_log",
        ["client_id"],
        postgresql_where=sa.text("client_id IS NOT NULL"),
    )

    # 3. ENABLE + FORCE RLS
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")

    # 4. Policy 3-way OR clause (project · client · legacy NULL)
    # Note: legacy/system rows (both NULL) visible cualquier tenant context
    # · acceptable porque rows generic audit trail · NO contienen PII project-bound.
    op.execute(
        """
        CREATE POLICY audit_log_isolation ON audit_log
          USING (
            project_id = current_project_id()
            OR client_id = current_client_id()
            OR (project_id IS NULL AND client_id IS NULL)
          )
        """
    )

    # 5. INSERT policy permisivo (servicios pueden emit rows · trigger sigue
    # validando hash chain · application layer responsable de tagging correctly
    # con project_id/client_id en NEW emit sites)
    op.execute(
        """
        CREATE POLICY audit_log_insert_permissive ON audit_log
          FOR INSERT WITH CHECK (true)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_log_insert_permissive ON audit_log")
    op.execute("DROP POLICY IF EXISTS audit_log_isolation ON audit_log")
    op.execute("ALTER TABLE audit_log NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_audit_log_client_id", table_name="audit_log")
    op.drop_index("ix_audit_log_project_id", table_name="audit_log")
    op.drop_column("audit_log", "client_id")
    op.drop_column("audit_log", "project_id")
