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
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import (
    require_marcos_or_client,
    require_owner,
)
from backend.app.auth.acceso_proyecto import asegurar_acceso_al_proyecto
from backend.app.database import get_db

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


async def _ensure_access(
    db: AsyncSession,
    project_id: uuid.UUID,
    request: Request,
) -> uuid.UUID:
    """Resuelve ownership + fija contexto de tenant + devuelve ``updated_by``.

    O2 · aqui vivia una copia del control de acceso que preguntaba por
    ``subject.pool`` y ``subject.user.is_marcos``, dos atributos que no existen
    en el modelo: la rama de administracion era inalcanzable y TODA peticion de
    Marcos acababa en la rama de cliente respondiendo 403. La regla vive ahora
    en ``auth/acceso_proyecto``, escrita una sola vez.
    """
    return await asegurar_acceso_al_proyecto(db, project_id, request)


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
