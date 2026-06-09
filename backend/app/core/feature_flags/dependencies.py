"""FastAPI dependencies para feature flags (ADR-036 SAN-D MB-17.2).

3 deps factory que retornan callables FastAPI Depends-compatible:

- ``require_feature(feature_key)`` · raise 403 si feature no aplica
  al proyecto (categoría/arquetipo/empleados).
- ``require_category(allowed_categories)`` · raise 403 si proyecto
  no tiene categoría permitida.
- ``require_archetype(allowed_archetypes)`` · raise 403 si arquetipo
  no permitido.

Ejemplo de uso::

    @router.post(
        "/projects/{project_id}/pentest/cpstic",
        dependencies=[Depends(require_category(["ALTA"]))],
    )
    async def trigger_pentest_cpstic(...):
        ...

Nota: la wire-up a endpoints existing M08/M21 se hace organicamente
cuando esos endpoints se tocan (ADR-036 Deferrables) · no batch
refactor en MB-17.2 para evitar romper test coverage actual.
"""
from __future__ import annotations

from typing import Awaitable, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.feature_flags import is_feature_applicable
from backend.app.database import get_db
from backend.app.models.core import Project


async def _load_project_with_client(
    db: AsyncSession,
    project_id: UUID,
) -> Project:
    """Eager load project + client (necesario para numero_empleados)."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.client))
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def require_feature(feature_key: str) -> Callable[..., Awaitable[None]]:
    """FastAPI dep · raise 403 si feature no aplica al proyecto."""

    async def dependency(
        project_id: UUID,
        db: AsyncSession = Depends(get_db),
    ) -> None:
        project = await _load_project_with_client(db, project_id)
        employee_count = project.client.numero_empleados if project.client else None

        applies = is_feature_applicable(
            feature_key,
            categoria=project.categoria_objetivo or "BASICA",
            archetype=project.archetype,
            employee_count=employee_count,
        )

        if not applies:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Feature '{feature_key}' no aplica a categoría "
                    f"{project.categoria_objetivo or 'BASICA'} · arquetipo "
                    f"{project.archetype or '(none)'}"
                ),
            )

    return dependency


def require_category(
    allowed_categories: list[str],
) -> Callable[..., Awaitable[None]]:
    """FastAPI dep · raise 403 si proyecto no es categoría permitida."""

    async def dependency(
        project_id: UUID,
        db: AsyncSession = Depends(get_db),
    ) -> None:
        project = await _load_project_with_client(db, project_id)
        cat = project.categoria_objetivo or "BASICA"
        if cat not in allowed_categories:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Endpoint requiere categoría {allowed_categories} · "
                    f"proyecto es {cat}"
                ),
            )

    return dependency


def require_archetype(
    allowed_archetypes: list[str],
) -> Callable[..., Awaitable[None]]:
    """FastAPI dep · raise 403 si arquetipo no permitido (lowercase enum)."""

    async def dependency(
        project_id: UUID,
        db: AsyncSession = Depends(get_db),
    ) -> None:
        project = await _load_project_with_client(db, project_id)
        if not project.archetype or project.archetype not in allowed_archetypes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Endpoint requiere arquetipo {allowed_archetypes} · "
                    f"proyecto es {project.archetype or '(none)'}"
                ),
            )

    return dependency
