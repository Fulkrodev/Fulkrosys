"""san_b_rls_21_tablas_tenant_sensitive

Revision ID: 33cef115cdf5
Revises: 83e27091b489
Create Date: 2026-05-04 13:52:59.890038

Habilita Row Level Security en 21 tablas tenant-sensitive identificadas
en SAN-B.MB-2.0 audit. Replica los patrones precedentes establecidos en
e41cd7163c02 (project_isolation/client_isolation simples) y
c8a3f2e1d4b5 (EXISTS subquery para FK indirecto).

Cobertura RLS: 87/176 → 108/176 tablas.

Cierra:
- TODO-FASE-13-RLS-CLIENT-TABLES-001 (3 client_* tables target original)
- Ampliación SAN-B.MB-2.0 audit (10 tablas tenant-data extras detectadas
  con FK project_id/client_id sin RLS)

Tablas excluidas deliberadamente (cross-tenant audit operacional):
- email_log, llm_interaction_log, connector_configs

Refs: SAN-B.MB-2.1
"""
from typing import Sequence, Union

from alembic import op


revision: str = '33cef115cdf5'
down_revision: Union[str, None] = '83e27091b489'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tablas con project_id directo · pattern simple
# (replica e41cd7163c02 pattern project_isolation)
PROJECT_ID_TABLES: tuple[str, ...] = (
    "dda_project_signatures",
    "diagnosis_runs",
    "evidence_renewal_requests",
    "external_pentester_handoffs",
    "lms_assignments",
    "magerit_analysis",
    "pkg_edges",
    "pkg_nodes",
    "retainer_quarterly_reports",
    "verification_findings",
    "verification_runs",
)

# Tablas con client_id directo · pattern simple
# (replica e41cd7163c02 pattern client_isolation)
CLIENT_ID_TABLES: tuple[str, ...] = (
    "client_user_audit",
    "client_users",
    "commercial_discounts",
)


def upgrade() -> None:
    # ── Bloque 1 · 11 tablas con project_id directo ─────────────────
    for table in PROJECT_ID_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )

    # ── Bloque 2 · 3 tablas con client_id directo ───────────────────
    for table in CLIENT_ID_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY client_isolation ON {table} "
            f"USING (client_id = current_client_id())"
        )

    # ── Bloque 3 · retainer_reports tiene project_id + client_id ────
    # Política OR · permite acceso vía cualquiera de los 2 contextos.
    op.execute("ALTER TABLE retainer_reports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE retainer_reports FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON retainer_reports "
        "USING ("
        "project_id = current_project_id() "
        "OR client_id = current_client_id()"
        ")"
    )

    # ── Bloque 4 · FK indirecto · pattern EXISTS subquery ───────────
    # Replica c8a3f2e1d4b5 invoice_lines/payment_reminders precedent.

    # categorizations.system_id → systems.project_id
    op.execute("ALTER TABLE categorizations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE categorizations FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON categorizations USING ("
        "EXISTS (SELECT 1 FROM systems s "
        "WHERE s.id = categorizations.system_id "
        "AND s.project_id = current_project_id()))"
    )

    # services.system_id → systems.project_id
    op.execute("ALTER TABLE services ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE services FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON services USING ("
        "EXISTS (SELECT 1 FROM systems s "
        "WHERE s.id = services.system_id "
        "AND s.project_id = current_project_id()))"
    )

    # document_versions.document_id → documents.project_id
    op.execute("ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_versions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON document_versions USING ("
        "EXISTS (SELECT 1 FROM documents d "
        "WHERE d.id = document_versions.document_id "
        "AND d.project_id = current_project_id()))"
    )

    # client_sessions.client_user_id → client_users.client_id
    op.execute("ALTER TABLE client_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_sessions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY client_isolation ON client_sessions USING ("
        "EXISTS (SELECT 1 FROM client_users cu "
        "WHERE cu.id = client_sessions.client_user_id "
        "AND cu.client_id = current_client_id()))"
    )

    # applied_safeguards y risk_treatments · cadena 3-nivel via assets
    # asset_threats.asset_id → assets.system_id → systems.project_id
    # (tablas legacy MAGERIT v1 · 0 rows actualmente · RLS preventivo)
    for table in ("applied_safeguards", "risk_treatments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} USING ("
            "EXISTS ("
            "SELECT 1 FROM asset_threats at "
            "JOIN assets a ON a.id = at.asset_id "
            "JOIN systems s ON s.id = a.system_id "
            f"WHERE at.id = {table}.asset_threat_id "
            "AND s.project_id = current_project_id()"
            "))"
        )


def downgrade() -> None:
    # Reverso completo · tablas vuelven a estado pre-SAN-B.MB-2.1.

    # FK indirecto subquery
    for table in (
        "applied_safeguards", "risk_treatments",
        "client_sessions", "document_versions",
        "services", "categorizations",
    ):
        op.execute(
            f"DROP POLICY IF EXISTS "
            f"{'client_isolation' if table == 'client_sessions' else 'project_isolation'} "
            f"ON {table}"
        )
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # retainer_reports dual
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON retainer_reports")
    op.execute("ALTER TABLE retainer_reports DISABLE ROW LEVEL SECURITY")

    # client_id directo
    for table in CLIENT_ID_TABLES:
        op.execute(f"DROP POLICY IF EXISTS client_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # project_id directo
    for table in PROJECT_ID_TABLES:
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
