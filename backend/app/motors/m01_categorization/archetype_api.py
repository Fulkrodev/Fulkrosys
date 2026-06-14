"""API 6 arquetipos PYME classification (SAN-C MB-11.6).

Endpoints
---------
- ``POST /api/v1/projects/{project_id}/classify-archetype``
  Ejecuta classifier deterministic + persiste archetype + confidence.
- ``GET /api/v1/projects/{project_id}/archetype``
  Retorna archetype persisted + workflow adjustments per arquetipo.

Wire-up frontend (ADR-034): ver
``frontend/lib/admin-archetype/api.ts`` + componente embebido en
ProjectInfoPanel.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.core import Client, Project
from backend.app.motors.m01_categorization.pyme_archetypes import (
    PymeArquetipo,
    archetype_workflow_adjustments,
    classify_archetype,
)

# ADR-013: el arquetipo es operación admin (Marcos). require_owner cierra el IDOR
# (antes el router no tenía dependencia de auth).
router = APIRouter(
    prefix="/projects",
    tags=["M01 - Pyme Archetypes"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    """FIX(RLS): projects es RLS fail-closed bajo fulkro_app · resolver owner via
    get_project_owner() SECURITY DEFINER + fijar tenant context antes de leer
    Project/Client (si no, db.get devuelve None → 404 en proyecto válido)."""
    owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(404, "Project not found")
    await set_tenant_context(db, client_id=owner, project_id=project_id)


class ArchetypeClassifyRequest(BaseModel):
    """Override de client_data para classify · campos opcionales.

    Si campos no provistos, classifier lee ``Client.sector`` como fallback.
    """

    cnae_code: Optional[str] = None
    sector: Optional[str] = None
    infrastructure_type: Optional[str] = None
    workforce_type: Optional[str] = None
    is_aapp_developer: Optional[bool] = None


class ArchetypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    archetype: str
    confidence: float
    reasoning_path: list[str]
    adjustments: dict


@router.post(
    "/{project_id}/classify-archetype",
    response_model=ArchetypeResponse,
)
async def post_classify_archetype(
    project_id: uuid.UUID,
    body: ArchetypeClassifyRequest,
    db: AsyncSession = Depends(get_db),
) -> ArchetypeResponse:
    """Ejecuta classifier deterministic y persiste archetype + confidence.

    Flujo:
    1. Lee project + client (HTTPException 404 si no existe).
    2. Construye client_data merging body + Client.sector fallback.
    3. Ejecuta ``classify_archetype`` (deterministic rules · sin LLM).
    4. Persiste ``project.archetype`` + ``project.archetype_confidence``.
    5. Retorna response con reasoning_path + adjustments.
    """
    await _set_project_rls(project_id, db)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    client = await db.get(Client, project.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")

    client_data: dict = {
        "cnae_code": body.cnae_code,
        "sector": body.sector or client.sector,
        "infrastructure_type": body.infrastructure_type,
        "workforce_type": body.workforce_type,
        "is_aapp_developer": body.is_aapp_developer,
    }

    result = classify_archetype(client_data)
    project.archetype = result.arquetipo.value
    project.archetype_confidence = result.confidence
    await db.commit()

    return ArchetypeResponse(
        archetype=result.arquetipo.value,
        confidence=float(result.confidence),
        reasoning_path=result.reasoning_path,
        adjustments=archetype_workflow_adjustments(result.arquetipo),
    )


@router.get(
    "/{project_id}/archetype",
    response_model=ArchetypeResponse,
)
async def get_project_archetype(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArchetypeResponse:
    """Retorna archetype persisted del proyecto + workflow adjustments.

    Si ``project.archetype`` es None (nunca clasificado), retorna 404
    para diferenciar de GENERICO explícito.
    """
    await _set_project_rls(project_id, db)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if not project.archetype:
        raise HTTPException(404, "Archetype not classified yet")

    try:
        arquetipo = PymeArquetipo(project.archetype)
    except ValueError as exc:
        raise HTTPException(500, "Stored archetype invalid") from exc

    return ArchetypeResponse(
        archetype=arquetipo.value,
        confidence=float(project.archetype_confidence or 0.0),
        reasoning_path=["Archetype persisted desde classify previo"],
        adjustments=archetype_workflow_adjustments(arquetipo),
    )
