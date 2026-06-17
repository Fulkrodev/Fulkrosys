"""Guard de propiedad transversal para endpoints multi-pool.

Contexto (raíz estructural, verificada en código):
``m21_portal_cliente/auth_service`` ejecuta ``SET LOCAL ROLE
fulkro_app_bypassrls`` durante TODO el request del pool cliente → **RLS OFF**.
Por tanto el aislamiento multi-tenant NO lo impone la BD: lo impone un check
explícito de propiedad **por-recurso** en código. Antes este check estaba
duplicado (m01 dimensions, m15 billing) o ausente (m21 approve_plan,
m_live_records, m24 IDMS, m07 renew/verify) → IDOR cross-tenant.

Este módulo centraliza el patrón canónico:

1. ``ensure_project_access(db, project_id, request)`` — resuelve el dueño del
   proyecto vía ``get_project_owner()`` (SECURITY DEFINER, cruza RLS), valida
   que el subject autenticado puede acceder (Marcos = todo; cliente = solo SU
   client_id), fija el tenant context y devuelve el ``client_id`` dueño.
2. ``assert_resource_in_project(resource_project_id, expected_project_id)`` —
   tras (1), cierra el IDOR por-recurso: el recurso (task/document/evidence…)
   debe pertenecer al proyecto ya verificado. Sin esto, un cliente con un
   project_id propio podía operar sobre un resource_id ajeno.

Convención de error: **404** tanto si el proyecto no existe como si existe pero
no es del cliente (no se filtra la existencia de recursos ajenos).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import _get_auth_subject
from backend.app.database import set_tenant_context
from backend.app.models.client_portal import ClientUser

__all__ = [
    "ensure_project_access",
    "ensure_project_access_for_user",
    "assert_resource_in_project",
]


async def ensure_project_access_for_user(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: object,
    *,
    set_context: bool = True,
) -> uuid.UUID:
    """Core de la verificación de acceso a partir del ``user`` ya resuelto
    (``User`` Marcos o ``ClientUser``, lo que devuelve ``require_marcos_or_client``).

    - ``ClientUser``: solo si el dueño del proyecto es su propio ``client_id``.
    - cualquier otro (``User`` Marcos): acceso a TODO proyecto.

    404 si el proyecto no existe o si un cliente accede a un proyecto ajeno.
    Fija el tenant context (client_id + project_id) salvo ``set_context=False``.
    Devuelve el ``client_id`` dueño.
    """
    owner = (
        await db.execute(
            text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    owner_id = uuid.UUID(str(owner))

    if isinstance(user, ClientUser) and str(user.client_id) != str(owner_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    if set_context:
        await set_tenant_context(db, client_id=owner_id, project_id=project_id)
    return owner_id


async def ensure_project_access(
    db: AsyncSession,
    project_id: uuid.UUID,
    request: Request,
    *,
    set_context: bool = True,
) -> uuid.UUID:
    """Verifica acceso a ``project_id`` desde la ``request`` y devuelve el
    ``client_id`` dueño. Resuelve el subject autenticado y delega en
    ``ensure_project_access_for_user``.
    """
    subject = _get_auth_subject(request)
    return await ensure_project_access_for_user(
        db, project_id, subject.user, set_context=set_context
    )


def assert_resource_in_project(
    resource_project_id: uuid.UUID | str | None,
    expected_project_id: uuid.UUID | str,
) -> None:
    """Cierra el IDOR por-recurso: ``resource_project_id`` debe coincidir con
    el ``expected_project_id`` (ya verificado por ``ensure_project_access``).

    404 si no coincide o el recurso no tiene project_id (no se filtra la
    existencia de recursos de otros tenants).
    """
    if resource_project_id is None or str(resource_project_id) != str(
        expected_project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
