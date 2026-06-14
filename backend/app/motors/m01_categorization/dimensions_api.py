"""Motor 1 Categorization · Dimensions API (sub-atom 1.C.D.A.0 v3.8).

REST endpoints para las 19 dimensiones del proyecto.

Endpoints (canónicos · single source of truth `projects` table):
  GET   /api/v1/projects/{id}/dimensions
        → lectura · require_marcos_or_client + ownership check
  PATCH /api/v1/admin/projects/{id}/dimensions
        → update · require_owner (Marcos only) · admin page consolidada

Captura distribuida natural complementaria:
  - m13_commercial: pre-venta · llama internamente DimensionsService
  - m_meetings: reunión exploratoria · llama internamente DimensionsService
  - m16_onboarding: cliente onboarding · llama internamente DimensionsService

OPS-038 sostenido (audit user_id UUID raw · 2 pools auth).
OPS-043 sostenido (await db.commit() explícito en service).
OPS-044 sostenido (BASE = "/projects" frontend · no double prefix).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import (
    require_marcos_or_client,
    require_owner,
)
from backend.app.database import get_db, set_tenant_context

from .dimensions_schemas import (
    ProjectDimensionsRead,
    ProjectDimensionsUpdate,
)
from .dimensions_service import (
    DimensionsService,
    ProjectDimensionsServiceError,
)


# Reader router: GET (admin + cliente · ownership-checked)
reader_router = APIRouter(
    prefix="/projects",
    tags=["Motor 1 - Categorization · Dimensions"],
)


# Admin router: PATCH (Marcos only · admin page consolidada)
admin_router = APIRouter(
    prefix="/admin/projects",
    tags=["Motor 1 - Categorization · Dimensions (admin)"],
    dependencies=[Depends(require_owner)],
)


# ================================================================
# Helpers
# ================================================================


def _subject_from_request(request: Request):
    """Resolve auth subject (AuthSubject) post require_* dependency."""
    return getattr(request.state, "auth_subject", None)


async def _ensure_access(
    db: AsyncSession,
    project_id: uuid.UUID,
    request: Request,
) -> uuid.UUID:
    """Resuelve ownership + retorna updated_by UUID.

    Marcos owner: acceso TODO · updated_by = subject.user.id (auth_users pool).
    Cliente: verify project_id pertenece a su client_id · updated_by =
    subject.user.id (client_users pool).

    FIX(RLS): `projects` es RLS fail-closed bajo fulkro_app, así que el service
    (select(Project)) devuelve 0 filas → 404 sin tenant context. Resolvemos el
    owner via get_project_owner() SECURITY DEFINER (cruza RLS) y fijamos el tenant
    context para AMBAS rutas — antes la admin no lo fijaba y la cliente dependía,
    frágil, de que verify_session dejara activo el rol bypassrls.
    """
    subject = _subject_from_request(request)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    pool = getattr(subject, "pool", None) or getattr(
        subject.user, "pool", None,
    )
    user_id = subject.user.id

    owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found",
        )

    # Admin Marcos: acceso TODO proyectos
    if pool == "auth_users" or getattr(subject.user, "is_marcos", False):
        await set_tenant_context(db, client_id=owner, project_id=project_id)
        return user_id

    # Cliente: verify ownership (owner == su client_id) · equivalente a
    # verify_client_owns_project pero robusto bajo RLS (get_project_owner cruza).
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


# ================================================================
# READ endpoint (admin + cliente)
# ================================================================


@reader_router.get(
    "/{project_id}/dimensions",
    response_model=ProjectDimensionsRead,
    dependencies=[Depends(require_marcos_or_client)],
)
async def get_project_dimensions(
    project_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProjectDimensionsRead:
    """Lee las 19 dimensiones del proyecto.

    Acceso:
      - Marcos (auth_users): TODO proyecto
      - Cliente (client_users): solo proyectos de SU client_id
    """
    await _ensure_access(db, project_id, request)
    service = DimensionsService(db)
    try:
        return await service.get_dimensions(project_id)
    except ProjectDimensionsServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


# ================================================================
# UPDATE endpoint (admin · Marcos only)
# ================================================================


@admin_router.patch(
    "/{project_id}/dimensions",
    response_model=ProjectDimensionsRead,
)
async def update_project_dimensions_admin(
    project_id: uuid.UUID,
    payload: ProjectDimensionsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProjectDimensionsRead:
    """Update parcial de las 19 dimensiones (admin Marcos).

    Source of truth canónico. Cualquier dim puede editarse cualquier momento.
    fase/categoria_objetivo/archetype NO se editan aquí (gestionados por
    motors respectivos).
    """
    updated_by = await _ensure_access(db, project_id, request)
    service = DimensionsService(db)
    try:
        return await service.update_dimensions(
            project_id=project_id,
            payload=payload,
            updated_by=updated_by,
        )
    except ProjectDimensionsServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc
