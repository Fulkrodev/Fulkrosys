"""¿Alcanza este sujeto a este proyecto? · una sola respuesta.

EL DEFECTO QUE ORIGINA ESTE MODULO
    Dos motores resolvian el acceso a un proyecto con el mismo bloque copiado:

        m01_categorization/dimensions_api._ensure_access
        m_workflow_engine/api._ensure_project_access

    y los dos preguntaban por un atributo que NO EXISTE:

        pool = getattr(subject, "pool", None) or getattr(subject.user, "pool", None)
        ...
        if pool == "auth_users" or getattr(subject.user, "is_marcos", False):

    ``AuthSubject`` declara ``__slots__ = ("user", "role_pool", "email")``: no
    hay ``pool``. Y ``User`` no tiene ``is_marcos`` (el unico ``_is_marcos`` del
    repo es una funcion privada de un middleware de fichajes). Los dos
    ``getattr`` devolvian siempre ``None``/``False``, asi que la rama de
    administracion era codigo inalcanzable: TODA peticion de Marcos caia en la
    rama de cliente, se quedaba sin ``client_id`` y respondia 403.

    El atributo correcto es ``role_pool``, que vale ``"marcos"`` o ``"cliente"``
    (``auth/global_dep.py``).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context

POOL_MARCOS = "marcos"


def es_marcos(subject: object) -> bool:
    """True si el sujeto autenticado viene del pool de administracion.

    Se lee ``role_pool`` y nada mas: cualquier ``getattr`` defensivo sobre un
    nombre que no existe convierte un fallo de autorizacion en un silencio.
    """
    return getattr(subject, "role_pool", None) == POOL_MARCOS


async def asegurar_acceso_al_proyecto(
    db: AsyncSession,
    project_id: uuid.UUID,
    request: Request,
) -> uuid.UUID:
    """Fija el contexto de tenant y devuelve el ``user_id`` para ``updated_by``.

    Marcos alcanza cualquier proyecto; un usuario cliente solo el suyo.

    El dueño se resuelve con ``get_project_owner()`` (SECURITY DEFINER, cruza
    RLS) porque ``projects`` es fail-closed bajo ``fulkro_app``: sin contexto de
    tenant un ``select(Project)`` devuelve cero filas y el endpoint respondería
    404 sobre un proyecto que existe.
    """
    subject = getattr(request.state, "auth_subject", None)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
        )
    user_id = subject.user.id

    owner = (await db.execute(
        _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found",
        )

    if es_marcos(subject):
        await set_tenant_context(db, client_id=owner, project_id=project_id)
        return user_id

    client_id = getattr(subject.user, "client_id", None)
    if client_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Identidad cliente sin client_id",
        )
    if str(owner) != str(client_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este proyecto",
        )
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return user_id
