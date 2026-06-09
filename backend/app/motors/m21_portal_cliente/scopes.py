"""M21 portal cliente · single-user-RW model · ADR-013 v3.

Decision arquitectonica: 1 usuario por cliente con 1 rol unico read+write.
NO multi-role · NO scopes granulares · NO role-management endpoints.

Roles ENS organizacionales (Sponsor · RI · RS · RSEG · RSIS · DPO) viven
en M28 project_role_assignments + M30 client_contacts (responsibilidades
del proyecto · NO permisos del portal · gestionados por Marcos).
"""
from __future__ import annotations

PORTAL_SCOPE = "rw"

__all__ = ["PORTAL_SCOPE"]
