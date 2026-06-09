"""Batch B diagnóstico previo · fix F-18 RLS account-less (SECURITY DEFINER).

El flujo account-less del lead (consume + /me/*) lee `magic_links` y
`onboarding_sessions` (ambas FORCE ROW LEVEL SECURITY · policy project_isolation
USING project_id = current_project_id()) SIN contexto tenant. En producción
(`fulkro_app`, NOSUPERUSER) `current_project_id()` = NULL → 0 filas → lectura
ciega (fail-closed F-18). En tests daba falso verde porque el fixture dejaba
`app.current_project_id` seteado del setup.

Fix mínimo-privilegio (NO usa SET LOCAL ROLE fulkro · RLS permanece activa para
el lead): dos resolvers SECURITY DEFINER que corren como owner (fulkro) y
exponen SOLO el project_id/client_id necesario para set_tenant_context() ANTES
de la lectura RLS:

- get_onboarding_session_owner(session_id) → (client_id, project_id) · /me/*
  (el session_id viaja en el header X-Onboarding-Session-Id).
- get_magic_link_project_by_token(token_hash) → project_id · /consume
  (el lead posee el token; sin él no se puede enumerar · mismo nivel de secreto
  que el propio magic-link).

Mirror del patrón existente `7c63d18af556_add_security_definer_owner_lookup`.
Additive · reversible · 0 filas afectadas.
"""
from __future__ import annotations

from alembic import op

revision = "precliente_rls_f18_001"
down_revision = "support_access_client_session_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION get_onboarding_session_owner(p_session_id UUID)
        RETURNS TABLE(client_id UUID, project_id UUID)
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
            SELECT p.client_id, s.project_id
            FROM onboarding_sessions s
            JOIN projects p ON p.id = s.project_id
            WHERE s.id = p_session_id;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION get_magic_link_project_by_token(p_token_hash TEXT)
        RETURNS UUID
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
            SELECT project_id FROM magic_links WHERE token_hash = p_token_hash;
        $$;
    """)

    op.execute("GRANT EXECUTE ON FUNCTION get_onboarding_session_owner(UUID) TO fulkro_app")
    op.execute("GRANT EXECUTE ON FUNCTION get_magic_link_project_by_token(TEXT) TO fulkro_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_magic_link_project_by_token(TEXT)")
    op.execute("DROP FUNCTION IF EXISTS get_onboarding_session_owner(UUID)")
