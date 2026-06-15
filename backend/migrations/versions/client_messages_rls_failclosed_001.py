"""client_messages_rls_failclosed_001 · §1.3 · RLS fail-OPEN -> fail-CLOSED

Auditoría 2026-06-15 §1.3: la policy ``client_isolation`` de ``client_messages``
(M29 client messaging · creada el 9-jun) quedó con la cláusula permisiva
``OR current_client_id() IS NULL`` y NO se incluyó en la pasada de hardening
``rls_fail_closed_hardening_001`` (11-jun). Como el pool cliente corre como
``fulkro_app`` (NOSUPERUSER · NOBYPASSRLS), una sesión SIN contexto de tenant
(GUC sin fijar → ``current_client_id()`` = NULL) pasaba el filtro y leía/escribía
mensajes de TODOS los clientes == fuga cross-tenant fail-OPEN.

Patrón canónico fail-CLOSED VIGENTE de este repo (mirror del estado real de
``email_log_tenant_isolation`` / ``signing_intents_tenant_isolation`` en la BD):
1. DROP de la policy fail-open ``client_isolation``.
2. CREATE policy fail-CLOSED única ``FOR ALL TO fulkro_app`` con filtro estricto
   ``client_id = current_client_id()`` (SIN ``OR current_client_id() IS NULL``).
3. ENABLE + FORCE ROW LEVEL SECURITY (idempotente).

IMPORTANTE — NO se crea policy ``admin_bypass TO fulkro_app_bypassrls USING(true)``:
``fulkro_app`` es miembro INHERIT de ``fulkro_app_bypassrls`` (init-roles.sql:100),
así que una policy permisiva ``TO fulkro_app_bypassrls`` se APLICA también al pool
cliente vía herencia → la haría fail-OPEN (verificado empíricamente: el pool
cliente vería TODAS las filas). El acceso admin NO necesita policy: los flujos
admin hacen ``SET LOCAL ROLE fulkro_app_bypassrls``, rol cuyo ATRIBUTO BYPASSRLS
salta la RLS por completo (independiente de policies). Por eso el estado canónico
actual de las tablas tenant ya NO tiene policies admin_bypass.

Los call-sites actuales ya fijan contexto (api_client.set_tenant_context) o elevan
a bypassrls (api_admin), así que el cierre NO rompe ningún flujo vivo.

Revision ID: client_messages_rls_failclosed_001
Revises: audit_hash_chain_secdef_001
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "client_messages_rls_failclosed_001"
down_revision: Union[str, None] = "audit_hash_chain_secdef_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE client_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_messages FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS client_isolation ON client_messages")
    op.execute(
        """
        CREATE POLICY client_messages_tenant_isolation ON client_messages
          FOR ALL TO fulkro_app
          USING (client_id = current_client_id())
          WITH CHECK (client_id = current_client_id())
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS client_messages_admin_bypass ON client_messages")
    op.execute("DROP POLICY IF EXISTS client_messages_tenant_isolation ON client_messages")
    op.execute(
        """
        CREATE POLICY client_isolation ON client_messages
          USING (client_id = current_client_id() OR current_client_id() IS NULL)
          WITH CHECK (client_id = current_client_id() OR current_client_id() IS NULL)
        """
    )
