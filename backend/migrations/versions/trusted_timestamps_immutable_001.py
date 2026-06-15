"""trusted_timestamps append-only ENFORCED por triggers (§1.8 audit-2026-06-15)

La tabla ``trusted_timestamps`` (sellos RFC 3161) se documentaba como "append-only"
pero sólo por convención: la migración original concedía UPDATE/DELETE a
``fulkro_app``/``fulkro_app_bypassrls`` y NO tenía triggers de inmutabilidad (a
diferencia de ``audit_log`` · fn_audit_log_immutable). Un token de sellado podía
alterarse desde el rol de la app. Esta migración lo blinda igual que audit_log:
  - función fn_trusted_timestamps_immutable() que lanza excepción en UPDATE/DELETE,
  - triggers BEFORE UPDATE / BEFORE DELETE,
  - REVOKE UPDATE, DELETE (sólo SELECT/INSERT · append-only real).

Aditiva e idempotente. NO toca datos.

Revision ID: trusted_timestamps_immutable_001
Revises: audit_2026_06_15_s15_columns_001
"""
from __future__ import annotations

from alembic import op

revision: str = "trusted_timestamps_immutable_001"
down_revision: str = "audit_2026_06_15_s15_columns_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_trusted_timestamps_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            RAISE EXCEPTION 'trusted_timestamps is append-only; % not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $fn$;
        """
    )
    op.execute(
        "DROP TRIGGER IF EXISTS tg_trusted_timestamps_no_update ON trusted_timestamps;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS tg_trusted_timestamps_no_delete ON trusted_timestamps;"
    )
    op.execute(
        """
        CREATE TRIGGER tg_trusted_timestamps_no_update
        BEFORE UPDATE ON trusted_timestamps
        FOR EACH ROW EXECUTE FUNCTION fn_trusted_timestamps_immutable();
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_trusted_timestamps_no_delete
        BEFORE DELETE ON trusted_timestamps
        FOR EACH ROW EXECUTE FUNCTION fn_trusted_timestamps_immutable();
        """
    )
    # Append-only real: el rol de la app sólo lee e inserta.
    op.execute(
        "REVOKE UPDATE, DELETE ON trusted_timestamps "
        "FROM fulkro_app, fulkro_app_bypassrls"
    )


def downgrade() -> None:
    op.execute(
        "GRANT UPDATE, DELETE ON trusted_timestamps "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS tg_trusted_timestamps_no_update ON trusted_timestamps;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS tg_trusted_timestamps_no_delete ON trusted_timestamps;"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_trusted_timestamps_immutable();")
