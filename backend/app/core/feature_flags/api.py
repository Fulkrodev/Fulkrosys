"""Feature flags REST endpoints (ADR-036 SAN-D MB-17.1 + ADR-046 MB-10 Atom 10.2).

5 endpoints:
- GET    /feature-flags/catalog                     · catalog YAML (estático)
- GET    /projects/{id}/feature-flags               · features evaluadas + overrides merged
- POST   /admin/feature-flags/override              · grant override (admin-only)
- DELETE /admin/feature-flags/override/{id}         · revoke override (admin-only)
- GET    /admin/feature-flags/overrides             · list overrides per project/client (admin-only)

Q5.3 cement: admin endpoints NO cliente-facing · INVISIBLE cliente pattern sostained.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, text

from backend.app.auth.dependencies import (
    require_marcos_or_client,
    require_owner,
)
from backend.app.core.feature_flags import load_feature_flags
from backend.app.core.feature_flags.service import (
    grant_override,
    list_overrides,
    resolve_project_features,
    revoke_override,
)
from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.models.core import Project

router = APIRouter(tags=["Feature Flags (MB-17)"])


@router.get("/feature-flags/catalog")
async def get_feature_flags_catalog():
    """Retorna catalog YAML completo · estático · sin DB call."""
    catalog = load_feature_flags()
    return catalog.model_dump()


@router.get("/projects/{project_id}/feature-flags")
async def get_project_feature_flags(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_marcos_or_client),
):
    """Retorna features aplicables a este proyecto (YAML + overrides merged).

    Sub-atom 1.C.C.A: dep cambiada de ``require_owner`` a
    ``require_marcos_or_client`` para que el portal cliente pueda
    consumir el endpoint. Ownership check explícito si el subject es
    ``ClientUser`` (mismo patrón que m27_conformity portal_api).

    Resolve eager-load ``Client.numero_empleados`` (DEC-1 · ADR-036)
    para evaluar features con ``requires_employee_count``. Aplica
    overrides activos (ADR-046 · MB-10 Atom 10.2) por encima del
    YAML eval cuando existen.
    """
    # RLS: la policy `client_id = current_client_id()` de projects oculta la fila
    # si no hay contexto seteado (el admin pool no trae client_id). Resolvemos el
    # owner vía get_project_owner (SECURITY DEFINER) y seteamos el contexto antes
    # de consultar (patrón canónico de los motores · sin esto el select devuelve
    # None → 404 falso para Marcos).
    owner_cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not owner_cid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    # Ownership check cliente ANTES de setear contexto (un cliente nunca debe
    # fijar el contexto RLS al client_id de otro). Marcos (admin pool) ve todo.
    if isinstance(current_user, ClientUser) and owner_cid != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(db, client_id=owner_cid, project_id=project_id)

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

    employee_count = (
        project.client.numero_empleados if project.client else None
    )
    features = await resolve_project_features(db, project)

    return {
        "categoria": project.categoria_objetivo or "BASICA",
        "archetype": project.archetype,
        "employee_count": employee_count,
        "features": features,
    }


# ══════════════════════════════════════════════════════════════════════
# ADR-046 · admin override management endpoints (Q5.3 admin-only)
# (renamed post-audit B1.2 · was ADR-037 MB-10 · collision fix)
# ══════════════════════════════════════════════════════════════════════


class GrantOverrideRequest(BaseModel):
    feature_key: str = Field(..., min_length=1, max_length=120)
    override_value: Any
    project_id: UUID | None = None
    client_id: UUID | None = None
    expires_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _scope_required(self) -> "GrantOverrideRequest":
        if self.project_id is None and self.client_id is None:
            raise ValueError(
                "project_id OR client_id required (al menos uno)"
            )
        return self


class OverrideResponse(BaseModel):
    id: UUID
    project_id: UUID | None
    client_id: UUID | None
    feature_key: str
    override_value: Any
    granted_at: datetime
    expires_at: datetime | None
    granted_by_user_id: UUID | None
    revoked_at: datetime | None
    revoked_by_user_id: UUID | None
    reason: str | None

    @classmethod
    def from_model(cls, row) -> "OverrideResponse":
        return cls(
            id=row.id,
            project_id=row.project_id,
            client_id=row.client_id,
            feature_key=row.feature_key,
            override_value=row.override_value,
            granted_at=row.granted_at,
            expires_at=row.expires_at,
            granted_by_user_id=row.granted_by_user_id,
            revoked_at=row.revoked_at,
            revoked_by_user_id=row.revoked_by_user_id,
            reason=row.reason,
        )


class RevokeOverrideRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


@router.post(
    "/admin/feature-flags/override",
    status_code=status.HTTP_201_CREATED,
    response_model=OverrideResponse,
)
async def admin_grant_feature_flag_override(
    body: GrantOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> OverrideResponse:
    """Grant override (admin-only · Q5.3 INVISIBLE cliente)."""
    override = await grant_override(
        db,
        feature_key=body.feature_key,
        override_value=body.override_value,
        granted_by_user_id=current_user.id,
        project_id=body.project_id,
        client_id=body.client_id,
        expires_at=body.expires_at,
        reason=body.reason,
    )
    await db.commit()
    return OverrideResponse.from_model(override)


@router.delete(
    "/admin/feature-flags/override/{override_id}",
    response_model=OverrideResponse,
)
async def admin_revoke_feature_flag_override(
    override_id: UUID,
    body: RevokeOverrideRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> OverrideResponse:
    """Revoke override (soft delete · admin-only)."""
    reason = body.reason if body is not None else None
    override = await revoke_override(
        db,
        override_id=override_id,
        revoked_by_user_id=current_user.id,
        reason=reason,
    )
    if override is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override not found or already revoked",
        )
    await db.commit()
    return OverrideResponse.from_model(override)


@router.get(
    "/admin/feature-flags/overrides",
    response_model=list[OverrideResponse],
)
async def admin_list_feature_flag_overrides(
    project_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    include_revoked: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> list[OverrideResponse]:
    """List overrides per project OR client (admin-only)."""
    if project_id is None and client_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id OR client_id required",
        )
    rows = await list_overrides(
        db,
        project_id=project_id,
        client_id=client_id,
        include_revoked=include_revoked,
    )
    return [OverrideResponse.from_model(r) for r in rows]
