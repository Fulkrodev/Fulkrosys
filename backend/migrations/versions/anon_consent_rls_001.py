"""Permitir filas anónimas (tenant_client_id IS NULL) en la RLS de fulkro_consent_audit_log.

`fulkro_pii_rls_002` aplicó una política tenant-estricta
``tenant_client_id = current_client_id()`` (fail-closed) a ``fulkro_consent_audit_log``.
Pero esa tabla almacena LEGÍTIMAMENTE el consentimiento de cookies de visitantes
ANÓNIMOS de fulkro.es: filas con ``tenant_client_id = NULL`` keyed por
``anonymous_session_id`` (ver m_compliance/cookies_api.post_consent/post_revoke, rama
anónima). El endpoint público ``/api/v1/legal/cookies/consent`` corre SIN auth, por lo
que NO hay ``SET ROLE fulkro_app_bypassrls`` y la sesión queda como ``fulkro_app`` con
RLS forzada. Resultado empírico: el INSERT anónimo fallaba con
``new row violates row-level security policy for table "fulkro_consent_audit_log"`` →
el banner de cookies de fulkro.es devolvía 500 y NO registraba el consentimiento
(incumplimiento LSSI/AEPD). Esto se enmascaró porque la suite corría contra una BD de
test en el head anterior (sin esta RLS); al avanzar la BD de test al head se destapó.

FIX: las filas de TENANT siguen aisladas (``tenant_client_id = current_client_id()``);
se admiten ADEMÁS las filas SIN tenant (anónimas, sin dueño). El predicado es
``OR tenant_client_id IS NULL`` (la fila no tiene tenant), NO ``OR current_client_id()
IS NULL`` (que sería la fuga fail-open documentada en rls-admin-bypass-policy-leaks /
client_messages_rls_failclosed). Un cliente autenticado corre bajo bypassrls y, aun sin
él, sus propias filas (tenant no nulo) siguen aisladas; solo se exponen las filas
anónimas (consentimientos de visitantes públicos, sin dato cross-tenant).

``fulkro_erasure_requests`` NO se toca: su flujo (Art.17) siempre lleva
``tenant_client_id`` (parámetro UUID obligatorio en request_erasure) → la política
estricta es correcta allí.

Aditiva e idempotente. NO toca datos.

Revision ID: anon_consent_rls_001
Revises: fulkro_pii_rls_002
"""
from __future__ import annotations

from alembic import op

revision: str = "anon_consent_rls_001"
down_revision: str = "fulkro_pii_rls_002"
branch_labels = None
depends_on = None

_TBL = "fulkro_consent_audit_log"
_POL = "fulkro_consent_audit_log_tenant_isolation"


def upgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_POL} ON {_TBL}")
    op.execute(
        f"CREATE POLICY {_POL} ON {_TBL} "
        "FOR ALL TO fulkro_app "
        "USING (tenant_client_id = current_client_id() OR tenant_client_id IS NULL) "
        "WITH CHECK (tenant_client_id = current_client_id() OR tenant_client_id IS NULL)"
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_POL} ON {_TBL}")
    op.execute(
        f"CREATE POLICY {_POL} ON {_TBL} "
        "FOR ALL TO fulkro_app "
        "USING (tenant_client_id = current_client_id()) "
        "WITH CHECK (tenant_client_id = current_client_id())"
    )
