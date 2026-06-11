"""rls_fail_closed_hardening_001 · ITEM R06 · RLS fail-OPEN -> fail-CLOSED

Audit ITEM R06: varias tablas tenant-sensitive tenían políticas RLS fail-OPEN
(cláusula permisiva ``OR current_project_id() IS NULL`` / ``OR project_id IS NULL``
/ ``OR client_id IS NULL``). Como el rol runtime del pool cliente es ``fulkro_app``
(NOSUPERUSER · NOBYPASSRLS), una sesión SIN contexto de tenant (GUC sin fijar ->
``current_project_id()`` = NULL) pasaba el filtro y leía filas de TODOS los proyectos
== fuga cross-tenant real.

Patrón canónico fail-CLOSED de este repo (mirror de los flujos reales verificados):
- El pool cliente corre como ``fulkro_app`` con ``set_config('app.current_project_id'...)``
  / ``set_config('app.current_client_id'...)`` (database.set_tenant_context).
- Los flujos admin/cron elevan explícitamente con ``SET LOCAL ROLE fulkro_app_bypassrls``
  (rol BYPASSRLS) -> NO dependen de cláusulas ``IS NULL`` para escapar la RLS.

Por tanto la corrección es:
1. DROP de las políticas fail-open.
2. CREATE de políticas fail-CLOSED puras ``FOR ALL TO fulkro_app`` con filtro estricto
   de tenant (project_id = current_project_id() [+ client_id = current_client_id()
   donde la tabla lo soporta], SIN ``OR ... IS NULL``).
3. Política de escape admin adicional ``FOR ALL TO fulkro_app_bypassrls USING(true)
   WITH CHECK(true)`` (belt+suspenders · el rol ya es BYPASSRLS, esta política sólo
   blinda contra drift de ownership/FORCE).
4. ENABLE + FORCE ROW LEVEL SECURITY en todas (idempotente).

Tablas tratadas: signing_intents · signing_events · signing_otp_codes ·
copilot_conversations · copilot_messages · email_log · oauth_state_tokens.

NOTA oauth_state_tokens: el callback OAuth (portal_oauth_callback) y el connect
(create_state) corrían como ``fulkro_app`` SIN fijar contexto de proyecto (el
state token ES el bearer que resuelve el proyecto). Para poder cerrar su RLS sin
romper el flujo, esos dos endpoints se elevan a ``fulkro_app_bypassrls`` (ver edit
de portal_api.py acompañante · el token es secreto bearer single-use + replay-guard).

NOTA email_log: las inserciones (EmailSender._persist_email_log) ya elevan a
fulkro_app_bypassrls, así que la política estricta sólo afecta la LECTURA del pool
cliente (futuro "mis emails recibidos"); se elimina la fuga ``client_id IS NULL``.

NOTA copilot_messages: NO tiene columna client_id; hereda el scope del padre vía
subconsulta a copilot_conversations (filtrada por client_id). Se mantiene el camino
project_id directo + la subconsulta de cliente; se elimina sólo ``project_id IS NULL``.

NOTA copilot_conversations: mantiene project_id = current_project_id() OR
client_id = current_client_id() (memoria copiloto cross-project per cliente legítima);
se elimina sólo ``project_id IS NULL``.

Revision ID: rls_fail_closed_hardening_001
Revises: unify_pricing_fiscal_rls_001
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op


revision: str = "rls_fail_closed_hardening_001"
down_revision: Union[str, None] = "unify_pricing_fiscal_rls_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ================================================================
    # signing_intents · fail-CLOSED project-scoped
    # ================================================================
    op.execute("ALTER TABLE signing_intents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE signing_intents FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS project_isolation_signing_intents ON signing_intents"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON signing_intents"
    )
    op.execute(
        """
        CREATE POLICY signing_intents_tenant_isolation ON signing_intents
          FOR ALL TO fulkro_app
          USING (project_id = current_project_id())
          WITH CHECK (project_id = current_project_id())
        """
    )
    op.execute(
        """
        CREATE POLICY signing_intents_admin_bypass ON signing_intents
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )

    # ================================================================
    # signing_events · fail-CLOSED project-scoped (INMUTABLE · NO update/delete grant)
    # ================================================================
    op.execute("ALTER TABLE signing_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE signing_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS project_isolation_signing_events ON signing_events"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON signing_events"
    )
    op.execute(
        """
        CREATE POLICY signing_events_tenant_isolation ON signing_events
          FOR ALL TO fulkro_app
          USING (project_id = current_project_id())
          WITH CHECK (project_id = current_project_id())
        """
    )
    op.execute(
        """
        CREATE POLICY signing_events_admin_bypass ON signing_events
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )

    # ================================================================
    # signing_otp_codes · fail-CLOSED via parent signing_intents (sin IS NULL)
    # ================================================================
    op.execute("ALTER TABLE signing_otp_codes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE signing_otp_codes FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS project_isolation_signing_otp_codes ON signing_otp_codes"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON signing_otp_codes"
    )
    op.execute(
        """
        CREATE POLICY signing_otp_codes_tenant_isolation ON signing_otp_codes
          FOR ALL TO fulkro_app
          USING (
            EXISTS (
              SELECT 1 FROM signing_intents si
              WHERE si.id = signing_otp_codes.signing_intent_id
                AND si.project_id = current_project_id()
            )
          )
          WITH CHECK (
            EXISTS (
              SELECT 1 FROM signing_intents si
              WHERE si.id = signing_otp_codes.signing_intent_id
                AND si.project_id = current_project_id()
            )
          )
        """
    )
    op.execute(
        """
        CREATE POLICY signing_otp_codes_admin_bypass ON signing_otp_codes
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )

    # ================================================================
    # copilot_conversations · fail-CLOSED (project OR client · sin project_id IS NULL)
    # ================================================================
    op.execute("ALTER TABLE copilot_conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE copilot_conversations FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS copilot_isolation ON copilot_conversations"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON copilot_conversations"
    )
    op.execute(
        """
        CREATE POLICY copilot_conversations_tenant_isolation ON copilot_conversations
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
    op.execute(
        """
        CREATE POLICY copilot_conversations_admin_bypass ON copilot_conversations
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )

    # ================================================================
    # copilot_messages · fail-CLOSED (project OR parent-conv-cliente · sin IS NULL)
    # (NO tiene client_id propio · hereda scope del padre copilot_conversations)
    # ================================================================
    op.execute("ALTER TABLE copilot_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE copilot_messages FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS copilot_messages_isolation ON copilot_messages"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON copilot_messages"
    )
    op.execute(
        """
        CREATE POLICY copilot_messages_tenant_isolation ON copilot_messages
          FOR ALL TO fulkro_app
          USING (
            project_id = current_project_id()
            OR conversation_id IN (
              SELECT id FROM copilot_conversations
              WHERE client_id = current_client_id()
            )
          )
          WITH CHECK (
            project_id = current_project_id()
            OR conversation_id IN (
              SELECT id FROM copilot_conversations
              WHERE client_id = current_client_id()
            )
          )
        """
    )
    op.execute(
        """
        CREATE POLICY copilot_messages_admin_bypass ON copilot_messages
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )

    # ================================================================
    # email_log · fail-CLOSED (client-scoped · sin client_id IS NULL read escape)
    # INSERTs ya van por fulkro_app_bypassrls (EmailSender._persist_email_log).
    # ================================================================
    op.execute("ALTER TABLE email_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE email_log FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS email_log_tenant_isolation ON email_log"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON email_log"
    )
    op.execute(
        """
        CREATE POLICY email_log_tenant_isolation ON email_log
          FOR ALL TO fulkro_app
          USING (client_id = current_client_id())
          WITH CHECK (client_id = current_client_id())
        """
    )
    op.execute(
        """
        CREATE POLICY email_log_admin_bypass ON email_log
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )

    # ================================================================
    # oauth_state_tokens · fail-CLOSED project-scoped.
    # El callback/connect se elevan a fulkro_app_bypassrls (ver portal_api.py edit);
    # el token es bearer secreto single-use. Pool cliente con contexto sólo ve los
    # del proyecto activo; sin contexto (NULL) NO ve ninguno (fail-CLOSED).
    # ================================================================
    op.execute("ALTER TABLE oauth_state_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oauth_state_tokens FORCE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS oauth_state_isolation ON oauth_state_tokens"
    )
    op.execute(
        "DROP POLICY IF EXISTS oauth_state_insert ON oauth_state_tokens"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON oauth_state_tokens"
    )
    op.execute(
        """
        CREATE POLICY oauth_state_tenant_isolation ON oauth_state_tokens
          FOR ALL TO fulkro_app
          USING (project_id = current_project_id())
          WITH CHECK (project_id = current_project_id())
        """
    )
    op.execute(
        """
        CREATE POLICY oauth_state_admin_bypass ON oauth_state_tokens
          FOR ALL TO fulkro_app_bypassrls
          USING (true) WITH CHECK (true)
        """
    )


def downgrade() -> None:
    # ---- oauth_state_tokens · restaurar políticas fail-open previas ----
    op.execute("DROP POLICY IF EXISTS oauth_state_admin_bypass ON oauth_state_tokens")
    op.execute("DROP POLICY IF EXISTS oauth_state_tenant_isolation ON oauth_state_tokens")
    op.execute(
        """
        CREATE POLICY oauth_state_isolation ON oauth_state_tokens
          USING (
            project_id = current_project_id()
            OR current_project_id() IS NULL
          )
        """
    )
    op.execute(
        """
        CREATE POLICY oauth_state_insert ON oauth_state_tokens
          FOR INSERT WITH CHECK (true)
        """
    )

    # ---- email_log · restaurar política previa (client_id IS NULL escape) ----
    op.execute("DROP POLICY IF EXISTS email_log_admin_bypass ON email_log")
    op.execute("DROP POLICY IF EXISTS email_log_tenant_isolation ON email_log")
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
        """
    )

    # ---- copilot_messages · restaurar policy 3-way con project_id IS NULL ----
    op.execute("DROP POLICY IF EXISTS copilot_messages_admin_bypass ON copilot_messages")
    op.execute("DROP POLICY IF EXISTS copilot_messages_tenant_isolation ON copilot_messages")
    op.execute(
        """
        CREATE POLICY copilot_messages_isolation ON copilot_messages
          USING (
            project_id = current_project_id()
            OR project_id IS NULL
            OR conversation_id IN (
              SELECT id FROM copilot_conversations
              WHERE client_id = current_client_id()
            )
          )
        """
    )

    # ---- copilot_conversations · restaurar policy 3-way con project_id IS NULL ----
    op.execute("DROP POLICY IF EXISTS copilot_conversations_admin_bypass ON copilot_conversations")
    op.execute("DROP POLICY IF EXISTS copilot_conversations_tenant_isolation ON copilot_conversations")
    op.execute(
        """
        CREATE POLICY copilot_isolation ON copilot_conversations
          USING (
            project_id = current_project_id()
            OR project_id IS NULL
            OR client_id = current_client_id()
          )
        """
    )

    # ---- signing_otp_codes · restaurar policy con OR ... IS NULL ----
    op.execute("DROP POLICY IF EXISTS signing_otp_codes_admin_bypass ON signing_otp_codes")
    op.execute("DROP POLICY IF EXISTS signing_otp_codes_tenant_isolation ON signing_otp_codes")
    op.execute(
        """
        CREATE POLICY project_isolation_signing_otp_codes ON signing_otp_codes
          FOR ALL
          USING (
            EXISTS (
              SELECT 1 FROM signing_intents si
              WHERE si.id = signing_otp_codes.signing_intent_id
                AND (
                  si.project_id = current_project_id()
                  OR current_project_id() IS NULL
                )
            )
          )
          WITH CHECK (
            EXISTS (
              SELECT 1 FROM signing_intents si
              WHERE si.id = signing_otp_codes.signing_intent_id
                AND (
                  si.project_id = current_project_id()
                  OR current_project_id() IS NULL
                )
            )
          )
        """
    )

    # ---- signing_events · restaurar policy con OR current_project_id() IS NULL ----
    op.execute("DROP POLICY IF EXISTS signing_events_admin_bypass ON signing_events")
    op.execute("DROP POLICY IF EXISTS signing_events_tenant_isolation ON signing_events")
    op.execute(
        """
        CREATE POLICY project_isolation_signing_events ON signing_events
          FOR ALL
          USING (
            project_id = current_project_id()
            OR current_project_id() IS NULL
          )
          WITH CHECK (
            project_id = current_project_id()
            OR current_project_id() IS NULL
          )
        """
    )

    # ---- signing_intents · restaurar policy con OR current_project_id() IS NULL ----
    op.execute("DROP POLICY IF EXISTS signing_intents_admin_bypass ON signing_intents")
    op.execute("DROP POLICY IF EXISTS signing_intents_tenant_isolation ON signing_intents")
    op.execute(
        """
        CREATE POLICY project_isolation_signing_intents ON signing_intents
          FOR ALL
          USING (
            project_id = current_project_id()
            OR current_project_id() IS NULL
          )
          WITH CHECK (
            project_id = current_project_id()
            OR current_project_id() IS NULL
          )
        """
    )
