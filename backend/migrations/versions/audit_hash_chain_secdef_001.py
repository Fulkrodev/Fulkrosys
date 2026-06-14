"""fn_audit_log_hash_chain SECURITY DEFINER · cadena R6 global (no por-tenant)

El trigger BEFORE INSERT calculaba hash_prev con un SELECT sobre audit_log que,
bajo el rol runtime fulkro_app + la RLS de audit_log (audit_log_isolation por
tenant), SOLO veía las filas del tenant actual → cada cliente encadenaba su
propia sub-cadena → la cadena hash R6 se BIFURCABA en producción (los tests no
lo cazan: el seed inserta bajo fulkro_migrate/BYPASSRLS, cadena global intacta).

Fix canónico: marcar la función como SECURITY DEFINER. Su owner es fulkro_migrate
(BYPASSRLS=true), así que el SELECT del predecesor lee SIEMPRE el MAX(seq) GLOBAL
ignorando la RLS del invocador. Aditiva e idempotente (CREATE OR REPLACE conserva
el trigger). search_path fijado (buena práctica SECURITY DEFINER).

Revision ID: audit_hash_chain_secdef_001
Revises: rr_triggered_by_widen_001
Create Date: 2026-06-14
"""
from alembic import op

revision = "audit_hash_chain_secdef_001"
down_revision = "rr_triggered_by_widen_001"
branch_labels = None
depends_on = None


_BODY = """
        DECLARE
            last_hash TEXT;
            payload   TEXT;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtext('audit_log_chain'));
            SELECT hash_current INTO last_hash
              FROM audit_log
              WHERE seq = (SELECT MAX(seq) FROM audit_log WHERE seq < NEW.seq);
            NEW.hash_prev := last_hash;
            payload := COALESCE(last_hash, '') || '|' ||
                       NEW.tabla || '|' ||
                       NEW.registro_id::text || '|' ||
                       NEW.accion || '|' ||
                       COALESCE(NEW.usuario, '') || '|' ||
                       NEW.timestamp::text || '|' ||
                       COALESCE(NEW.payload_old::text, '') || '|' ||
                       COALESCE(NEW.payload_new::text, '');
            NEW.hash_current := encode(digest(payload, 'sha256'), 'hex');
            RETURN NEW;
        END;
"""


def upgrade() -> None:
    op.execute(
        "CREATE OR REPLACE FUNCTION fn_audit_log_hash_chain() RETURNS trigger\n"
        "LANGUAGE plpgsql\n"
        "SECURITY DEFINER\n"
        "SET search_path = public, pg_catalog\n"
        "AS $fn$" + _BODY + "$fn$;"
    )


def downgrade() -> None:
    # Vuelve a SECURITY INVOKER (comportamiento original · con bifurcación bajo RLS).
    op.execute(
        "CREATE OR REPLACE FUNCTION fn_audit_log_hash_chain() RETURNS trigger\n"
        "LANGUAGE plpgsql\n"
        "AS $fn$" + _BODY + "$fn$;"
    )
