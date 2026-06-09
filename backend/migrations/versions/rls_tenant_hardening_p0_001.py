"""rls_tenant_hardening_p0 · cierra aislamiento multi-tenant (auditoria seguridad 2026-06-07)

Revision ID: rls_tenant_hardening_p0_001
Revises: milestone_scheduled_date_28_001
Create Date: 2026-06-07

P0 seguridad · dos bloques:

BLOQUE A · 7 tablas tenant-sensitive SIN NINGUN RLS (relrowsecurity=f, 0 policies).
Como `fulkro_app` (rol runtime, NO owner, NO bypassrls) consultaba estas tablas sin
ninguna policy, leia filas de TODOS los proyectos -> fuga cross-tenant real. Todas
tienen `project_id` directo. Se replica el patron canonico 33cef115cdf5
(ENABLE + FORCE + POLICY project_isolation USING project_id = current_project_id()).
Varias son cliente-reachable (audit_accompaniment_* via GET /client-portal/accompaniment/
timeline), invoices_aapp (financiero) y aepd_notifications (brechas RGPD) -> sensibles.

BLOQUE B · 26 tablas con RLS ENABLED pero NOT FORCED. En el build de produccion el owner
es `fulkro_migrate` (BYPASSRLS) != rol app, asi que ya estan enforced para `fulkro_app`;
FORCE es defensa-en-profundidad contra drift de ownership (si una tabla pasara a ser
propiedad del rol app, sin FORCE el owner bypassaria su propia policy). fulkro_migrate
tiene BYPASSRLS -> FORCE no afecta a migraciones/seeds. Funcionalmente no-op, blinda futuro.

Reversible. Patron USING = WITH CHECK por defecto (igual que 33cef115cdf5).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "rls_tenant_hardening_p0_001"
down_revision: Union[str, None] = "milestone_scheduled_date_28_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── BLOQUE A · 7 tablas tenant SIN RLS · project_id directo ──────────
NEW_RLS_TABLES: tuple[str, ...] = (
    "bia_analyses",
    "awareness_sessions",
    "invoices_aapp",
    "aepd_notifications",
    "audit_accompaniment_state",
    "audit_accompaniment_transitions",
    "audit_accompaniment_artifacts",
)

# ── BLOQUE B · 26 tablas RLS-enabled NOT forced · solo anadir FORCE ──
# (ya tienen su policy; owner=fulkro_migrate BYPASSRLS -> FORCE es hardening)
FORCE_ONLY_TABLES: tuple[str, ...] = (
    "ai_act_transparency_events",
    "alert_queue",
    "audit_dry_run_results",
    "chat_messages",
    "chat_threads",
    "client_notifications",
    "client_tasks",
    "cloud_connectors",
    "cloud_digest_snapshots",
    "cloud_gaps",
    "cloud_remediation_approval_logs",
    "cloud_resources",
    "cloud_sync_jobs",
    "connector_configs",
    "contract_milestones",
    "departments",
    "email_log",
    "live_records",
    "notification_events",
    "notification_preferences",
    "retainer_health_signals",
    "signing_events",
    "signing_intents",
    "signing_otp_codes",
    "whatsapp_messages",
    "whatsapp_threads",
)


def upgrade() -> None:
    # BLOQUE A · habilitar RLS + policy project_isolation en las 7 tablas
    for table in NEW_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )

    # BLOQUE B · solo FORCE (la policy ya existe)
    for table in FORCE_ONLY_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # BLOQUE B · quitar FORCE (vuelven a enabled-not-forced)
    for table in FORCE_ONLY_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")

    # BLOQUE A · revertir RLS completo
    for table in NEW_RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
