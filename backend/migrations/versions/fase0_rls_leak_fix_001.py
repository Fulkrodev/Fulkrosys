"""fase0_rls_leak_fix_001 · P0 · cierra fuga cross-tenant de FASE 0 (R06)

INCIDENTE (verificado empíricamente sobre el head real con una conexión REAL como
``fulkro_app``): el rol runtime ``fulkro_app`` (NOSUPERUSER, NOBYPASSRLS) veía
filas de OTROS clientes en 7 tablas ENS-sensibles, pese a fijar el contexto del
cliente propio.

CAUSA RAÍZ:
  * ``init-roles.sql`` hace ``GRANT fulkro_app_bypassrls TO fulkro_app`` (necesario
    para que el admin pueda ``SET LOCAL ROLE fulkro_app_bypassrls``). Con INHERIT,
    ``fulkro_app`` es MIEMBRO del rol bypass.
  * R06 (``rls_fail_closed_hardening_001``) creó, como "escape admin", políticas
    permisivas ``<tabla>_admin_bypass FOR ALL TO fulkro_app_bypassrls USING(true)
    WITH CHECK(true)``.
  * En PostgreSQL una política ``TO rol`` aplica también a los MIEMBROS de ese rol
    → ``<tabla>_admin_bypass`` aplica a ``fulkro_app``. Las políticas permisivas se
    combinan con OR; ``USING(true)`` hace visible TODA fila → ``fulkro_app`` veía
    todos los tenants. (R08 ``rls_canonical_policies_002`` ya lo hizo bien: SIN
    política de bypass, confiando en el ATRIBUTO ``BYPASSRLS`` del rol, que NO se
    hereda por pertenencia.)

FIX: eliminar las 7 políticas ``*_admin_bypass``. El rol ``fulkro_app_bypassrls``
sigue saltando RLS por su ATRIBUTO (no necesita política); ``fulkro_app`` queda
sujeto únicamente a ``*_tenant_isolation`` (fail-closed) → aislamiento restaurado.

PROBADO (transacción, rolled back): con la política → ``fulkro_app`` ctx=A ve A y
B; sin la política → ve solo A; sin contexto → 0 filas.

Tablas afectadas (7): signing_intents, signing_events, signing_otp_codes,
copilot_conversations, copilot_messages, email_log, oauth_state_tokens.

Revision ID: fase0_rls_leak_fix_001
Revises: e155_scope_model_001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op


revision: str = "fase0_rls_leak_fix_001"
down_revision: Union[str, None] = "e155_scope_model_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (tabla, nombre de la política admin_bypass) · tal como las creó R06.
_ADMIN_BYPASS_POLICIES = [
    ("signing_intents", "signing_intents_admin_bypass"),
    ("signing_events", "signing_events_admin_bypass"),
    ("signing_otp_codes", "signing_otp_codes_admin_bypass"),
    ("copilot_conversations", "copilot_conversations_admin_bypass"),
    ("copilot_messages", "copilot_messages_admin_bypass"),
    ("email_log", "email_log_admin_bypass"),
    ("oauth_state_tokens", "oauth_state_admin_bypass"),
]


def upgrade() -> None:
    # P0 · eliminar las políticas permisivas USING(true) que filtraban a fulkro_app
    # (miembro de fulkro_app_bypassrls). El bypass admin sigue vivo por el ATRIBUTO
    # BYPASSRLS del rol fulkro_app_bypassrls (SET LOCAL ROLE), no por política.
    for table, policy in _ADMIN_BYPASS_POLICIES:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")

    # email_log · restaurar la visibilidad system-wide (client_id IS NULL) que R06
    # perdió al endurecer a ``client_id = current_client_id()``. Las filas sin
    # cliente (leads / notificaciones de sistema) deben verse desde cualquier
    # contexto; NO es un leak (NULL no es de ningún tenant). Mirror del
    # comportamiento documentado pre-R06. (signing/copilot/oauth usan project_id y
    # no tienen concepto system-wide → no necesitan cláusula NULL.)
    op.execute("DROP POLICY IF EXISTS email_log_tenant_isolation ON email_log")
    op.execute(
        "CREATE POLICY email_log_tenant_isolation ON email_log "
        "FOR ALL TO fulkro_app "
        "USING (client_id IS NULL OR client_id = current_client_id()) "
        "WITH CHECK (client_id IS NULL OR client_id = current_client_id())"
    )


def downgrade() -> None:
    # Restaura email_log_tenant_isolation a la forma estricta de R06.
    op.execute("DROP POLICY IF EXISTS email_log_tenant_isolation ON email_log")
    op.execute(
        "CREATE POLICY email_log_tenant_isolation ON email_log "
        "FOR ALL TO fulkro_app "
        "USING (client_id = current_client_id()) "
        "WITH CHECK (client_id = current_client_id())"
    )
    # Recrea las políticas admin_bypass tal como las dejó R06 (reversibilidad).
    # NOTA: restaurarlas REINTRODUCE la fuga cross-tenant descrita arriba.
    for table, policy in _ADMIN_BYPASS_POLICIES:
        op.execute(
            f"CREATE POLICY {policy} ON {table} "
            f"FOR ALL TO fulkro_app_bypassrls "
            f"USING (true) WITH CHECK (true)"
        )
