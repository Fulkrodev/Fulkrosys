"""rls_canonical_policies_002 · ITEM R08 · canonizar policies admin_all USING(true)

Audit ITEM R08: 5 políticas RLS no aislaban por tenant:
- change_topologies (m28) · POLICY admin_all USING(true) WITH CHECK(true)
- conformity_state_snapshots (m27) · POLICY admin_all USING(true) WITH CHECK(true)
- client_contacts (m30) · POLICY admin_all USING(true) WITH CHECK(true)
- client_contact_interactions (m30) · POLICY admin_all USING(true) WITH CHECK(true)
- ai_act_transparency_events · raw current_setting('app.current_project_id') sin
  helper canónico y SIN escape client_id pese a columna client_id nullable.

Hoy NO fugan (sus routers son require_owner y los flujos admin elevan a
fulkro_app_bypassrls), pero las políticas deben canonizarse al patrón fail-closed
del repo (project_id = current_project_id() [+ client_id = current_client_id()
donde la tabla lo soporta]; bypass admin por ATRIBUTO de rol, no por USING(true)).

Columnas reales (information_schema · verificado live):
- change_topologies / conformity_state_snapshots: project_id NOT NULL (sin client_id).
- client_contacts: client_id NOT NULL + project_id NULLABLE.
- client_contact_interactions: sólo contact_id (FK) → aislamiento por subquery al padre.
- ai_act_transparency_events: project_id NOT NULL + client_id NULLABLE.

Revision ID: rls_canonical_policies_002
Revises: rls_fail_closed_hardening_001
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op


revision: str = "rls_canonical_policies_002"
down_revision: Union[str, None] = "rls_fail_closed_hardening_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ITEM R08 · canonizar policies RLS context-aware.
    # Reemplaza admin_all USING(true) (m27/m28/m30) y el raw current_setting
    # de ai_act por el patron canonico current_project_id()/current_client_id().
    # El bypass admin NO va en la policy: lo aporta el ATRIBUTO de rol
    # fulkro_app_bypassrls (BYPASSRLS); los handlers admin hacen
    # SET LOCAL ROLE fulkro_app_bypassrls. fulkro_migrate (owner, BYPASSRLS)
    # tampoco se ve afectado por FORCE. Sin OR...IS NULL permisivo.

    # ── m28 · change_topologies (project_id NOT NULL · sin client_id) ──
    op.execute("DROP POLICY IF EXISTS admin_all ON change_topologies")
    op.execute("ALTER TABLE change_topologies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE change_topologies FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY project_isolation ON change_topologies
          USING (project_id = current_project_id())
          WITH CHECK (project_id = current_project_id())
        """
    )

    # ── m27 · conformity_state_snapshots (project_id NOT NULL · sin client_id) ──
    op.execute(
        "DROP POLICY IF EXISTS admin_all ON conformity_state_snapshots"
    )
    op.execute(
        "ALTER TABLE conformity_state_snapshots ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE conformity_state_snapshots FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY project_isolation ON conformity_state_snapshots
          USING (project_id = current_project_id())
          WITH CHECK (project_id = current_project_id())
        """
    )

    # ── m30 · client_contacts (client_id NOT NULL · project_id NULLABLE) ──
    # Scope primario por cliente; la cláusula project deja aflorar contactos
    # project-bound bajo contexto de proyecto. Contactos históricos
    # (project_id NULL) sólo visibles por client_id = current_client_id().
    op.execute("DROP POLICY IF EXISTS admin_all ON client_contacts")
    op.execute("ALTER TABLE client_contacts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_contacts FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON client_contacts
          USING (
            client_id = current_client_id()
            OR project_id = current_project_id()
          )
          WITH CHECK (
            client_id = current_client_id()
            OR project_id = current_project_id()
          )
        """
    )

    # ── m30 · client_contact_interactions (sólo contact_id) ──
    # Sin columna tenant directa: hereda el scope del contacto padre vía
    # subquery (mirror copilot_messages_isolation).
    op.execute(
        "DROP POLICY IF EXISTS admin_all ON client_contact_interactions"
    )
    op.execute(
        "ALTER TABLE client_contact_interactions ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE client_contact_interactions FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY parent_tenant_isolation ON client_contact_interactions
          USING (
            contact_id IN (
              SELECT id FROM client_contacts
              WHERE client_id = current_client_id()
                 OR project_id = current_project_id()
            )
          )
          WITH CHECK (
            contact_id IN (
              SELECT id FROM client_contacts
              WHERE client_id = current_client_id()
                 OR project_id = current_project_id()
            )
          )
        """
    )

    # ── ai_act_transparency_events (project_id NOT NULL · client_id NULLABLE) ──
    # Canoniza raw current_setting(...) → current_project_id() y añade
    # escape client_id = current_client_id() (la tabla fue diseñada para
    # cross-project cliente queries · client_id nullable por diseño).
    op.execute(
        "DROP POLICY IF EXISTS ai_act_transparency_project_isolation "
        "ON ai_act_transparency_events"
    )
    op.execute(
        "ALTER TABLE ai_act_transparency_events ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE ai_act_transparency_events FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY ai_act_transparency_isolation
          ON ai_act_transparency_events
          FOR ALL TO fulkro_app
          USING (
            project_id = current_project_id()
            OR client_id = current_client_id()
          )
          WITH CHECK (
            project_id = current_project_id()
            OR client_id = current_client_id()
          )
        """
    )


def downgrade() -> None:
    # Revertir a las policies originales (USING(true) admin_all m27/m28/m30 +
    # raw current_setting project-only en ai_act).

    # ── ai_act_transparency_events · restaurar policy raw original ──
    op.execute(
        "DROP POLICY IF EXISTS ai_act_transparency_isolation "
        "ON ai_act_transparency_events"
    )
    op.execute(
        """
        CREATE POLICY ai_act_transparency_project_isolation
          ON ai_act_transparency_events
          FOR ALL TO fulkro_app
          USING (
            project_id::text = current_setting('app.current_project_id', true)
          )
          WITH CHECK (
            project_id::text = current_setting('app.current_project_id', true)
          )
        """
    )

    # ── client_contact_interactions · restaurar admin_all ──
    op.execute(
        "DROP POLICY IF EXISTS parent_tenant_isolation "
        "ON client_contact_interactions"
    )
    op.execute(
        "CREATE POLICY admin_all ON client_contact_interactions "
        "USING (true) WITH CHECK (true)"
    )

    # ── client_contacts · restaurar admin_all ──
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON client_contacts")
    op.execute(
        "CREATE POLICY admin_all ON client_contacts "
        "USING (true) WITH CHECK (true)"
    )

    # ── conformity_state_snapshots · restaurar admin_all ──
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON conformity_state_snapshots"
    )
    op.execute(
        "CREATE POLICY admin_all ON conformity_state_snapshots "
        "USING (true) WITH CHECK (true)"
    )

    # ── change_topologies · restaurar admin_all ──
    op.execute("DROP POLICY IF EXISTS project_isolation ON change_topologies")
    op.execute(
        "CREATE POLICY admin_all ON change_topologies "
        "USING (true) WITH CHECK (true)"
    )
