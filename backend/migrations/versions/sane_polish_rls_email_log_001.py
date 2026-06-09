"""Sprint Polish block 4 · apply RLS email_log defense-in-depth.

ISO 27001 A.8.20 · preparado RGPD art. 15 portal cliente futuro
(endpoint "mis emails recibidos" cuando exista · RLS protege leak).

Honor MB-9 atom 9.3 decisions previas (verified audit empirical 2026-05-12):
- oauth_state_tokens · transient 10min TTL + cleanup active · KEEP DEFER
- llm_interaction_log · admin-only · 0 portal cliente exposure · KEEP DEFER

SKIP RLS marcos_timesheet_entries · diseño cross-cliente intencional
(Marcos cockpit aggregation across clients · admin-only RLS rompería
use case sin valor real).

Policy design notes:
- USING strict tenant filter (READ side defense-in-depth)
- WITH CHECK permissive:
  · NULL client_id allowed (system-wide emails pre-cliente · lead phase)
  · current_client_id() NULL allowed (admin/cron flows sin tenant context)
  · client_id = current_client_id() matching (cliente authenticated flows)
  Esto evita romper email_sender flows existing que hacen
  SET LOCAL ROLE fulkro pero NO siempre setean app.current_client_id.

Revision ID: sane_polish_rls_email_log_001
Revises: sane_mb9bis_norma_rep_001
Create Date: 2026-05-12
"""
from alembic import op


revision = "sane_polish_rls_email_log_001"
down_revision = "sane_mb9bis_norma_rep_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Re-asignar owner a fulkro_migrate (consistencia con tablas RLS-protegidas MB-9):
    # fulkro_app es miembro de fulkro (table owner original · superuser) y, por
    # herencia de membership, queries de fulkro_app bypasaban la RLS de email_log.
    # alert_queue (owner=fulkro_migrate) sí filtra porque fulkro_app NO es miembro
    # de fulkro_migrate. Cambiar owner a fulkro_migrate restaura el patrón correcto.
    op.execute("ALTER TABLE email_log OWNER TO fulkro_migrate")
    op.execute("ALTER TABLE email_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY email_log_tenant_isolation ON email_log
        FOR ALL TO fulkro_app
        USING (
            client_id IS NULL
            OR client_id = current_client_id()
        )
        WITH CHECK (
            client_id IS NULL
            OR current_client_id() IS NULL
            OR client_id = current_client_id()
        )
        """,
    )
    # Re-grant CRUD post-RLS enable (consistent with sane_mb9_rls_focused_002 pattern).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON email_log TO fulkro_app",
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS email_log_tenant_isolation ON email_log",
    )
    op.execute("ALTER TABLE email_log DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE email_log OWNER TO fulkro")
