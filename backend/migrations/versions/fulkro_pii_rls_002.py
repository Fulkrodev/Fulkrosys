"""RLS en tablas PII tenant fuera del barrido (§1.3 audit-2026-06-15)

Dos tablas con PII por tenant escaparon el barrido RLS porque su columna de tenant
es ``tenant_client_id`` (no client_id/project_id):
  - fulkro_consent_audit_log  (consentimientos RGPD · user_id, ip, user_agent, …)
  - fulkro_erasure_requests   (derecho de supresión Art.17 · tombstone_data, …)
Ambas tenían relrowsecurity=false y 0 policies. Aunque el portal cliente corre hoy
bajo fulkro_app_bypassrls (el aislamiento real lo dan los filtros app-layer), el
modelo multi-tenant exige el muro RLS de defensa en profundidad en TODA tabla con
tenant. Se aplica el patrón fail-CLOSED canónico (client_messages_rls_failclosed):
política ÚNICA ``FOR ALL TO fulkro_app`` con predicado estricto, SIN ``admin_bypass``
(el admin bypasea por el ATRIBUTO BYPASSRLS del rol, no por policy · evita la fuga
por herencia INHERIT documentada en rls-admin-bypass-policy-leaks).

Aditiva e idempotente. NO toca datos (tablas vacías).

Revision ID: fulkro_pii_rls_002
Revises: trusted_timestamps_immutable_001
"""
from __future__ import annotations

from alembic import op

revision: str = "fulkro_pii_rls_002"
down_revision: str = "trusted_timestamps_immutable_001"
branch_labels = None
depends_on = None

_TABLES = ("fulkro_consent_audit_log", "fulkro_erasure_requests")


def upgrade() -> None:
    for tbl in _TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {tbl}_tenant_isolation ON {tbl}")
        op.execute(
            f"CREATE POLICY {tbl}_tenant_isolation ON {tbl} "
            "FOR ALL TO fulkro_app "
            "USING (tenant_client_id = current_client_id()) "
            "WITH CHECK (tenant_client_id = current_client_id())"
        )


def downgrade() -> None:
    for tbl in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS {tbl}_tenant_isolation ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
