"""oauth_state_rls_001 · RLS defense-in-depth para oauth_state_tokens (FIX P4-2c)

oauth_state_tokens (anti-CSRF state per OAuth flow · client_user_id + project_id
scope) era la única tabla tenant-scoped sin RLS. Esta migración la alinea con el
patrón canónico (mirror audit_log_rls_001):

1. ENABLE + FORCE ROW LEVEL SECURITY
2. Policy SELECT/UPDATE/DELETE context-aware:
     project_id = current_project_id()
     OR current_project_id() IS NULL   -- callback OAuth pre-contexto
3. Policy INSERT permisiva (create_state genera el token antes del contexto)

⚠️ CLAVE · NO romper el callback OAuth: ``validate_and_consume`` busca el token por
``state_token`` (único) ANTES de que exista contexto de proyecto (el propio token ES
lo que resuelve el proyecto). La cláusula ``OR current_project_id() IS NULL`` garantiza
que ese lookup sin contexto siga viendo la fila (el token se autovalida por unicidad +
guard de replay ``consumed_at``). Con contexto fijado, sólo se ven los tokens del
proyecto activo (aislamiento defense-in-depth para cualquier rol least-privilege futuro;
el rol runtime ``fulkro_app`` es BYPASSRLS, así que en producción es capa adicional).

Revision ID: oauth_state_rls_001
Revises: pricing_config_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "oauth_state_rls_001"
down_revision: Union[str, None] = "pricing_config_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE oauth_state_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oauth_state_tokens FORCE ROW LEVEL SECURITY")

    # SELECT/UPDATE/DELETE · context-aware (NULL-context escape preserva el callback)
    op.execute(
        """
        CREATE POLICY oauth_state_isolation ON oauth_state_tokens
          USING (
            project_id = current_project_id()
            OR current_project_id() IS NULL
          )
        """
    )

    # INSERT permisivo · create_state emite el token antes de fijar contexto.
    op.execute(
        """
        CREATE POLICY oauth_state_insert ON oauth_state_tokens
          FOR INSERT WITH CHECK (true)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS oauth_state_insert ON oauth_state_tokens")
    op.execute("DROP POLICY IF EXISTS oauth_state_isolation ON oauth_state_tokens")
    op.execute("ALTER TABLE oauth_state_tokens NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE oauth_state_tokens DISABLE ROW LEVEL SECURITY")
