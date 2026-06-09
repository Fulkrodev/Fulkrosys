"""Auth constants — valores válidos del campo ``User.role`` (ADR-015).

``role`` vive en BD como columna invariante del usuario. Capabilities
operacionales delegables viven en Settings, no aquí. Regla
mnemotécnica:

- ¿Define qué ES el usuario? → BD (columna ``role``, valores aquí)
- ¿Define qué PUEDE HACER en este momento? → Settings (capabilities)

``ALLOWED_ROLES`` es ``frozenset`` para usarse como guardia inmutable
en validaciones de service layer. NO es Enum SQLAlchemy intencionalmente
(extensibilidad sin migración Alembic — añadir un valor nuevo aquí no
requiere ALTER TABLE).
"""
from __future__ import annotations


ALLOWED_ROLES: frozenset[str] = frozenset(
    {
        "owner",
        "client_user",
        "partner_senior",
        "pentester_external",
        "introducer",
    }
)


def is_role_allowed(role: str) -> bool:
    """Devuelve True si ``role`` está en :data:`ALLOWED_ROLES`."""
    return role in ALLOWED_ROLES
