"""Feature flag overrides service layer (ADR-046 materializa ADR-036 deferred).

Async CRUD para ``FeatureFlagOverride`` + helper merge YAML defaults +
overrides per project.

Precedence resolve_project_features:
  1. project-level override activo (project_id matching · revoked_at NULL ·
     expires_at futuro o NULL)
  2. client-level override activo (matching via Project.client_id)
  3. YAML catalog evaluation (get_features_for_project · ADR-036)

Q5.3 cement: cliente UI INVISIBLE · estos helpers admin-only (require_owner)
in API layer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.feature_flags import get_features_for_project
from backend.app.core.feature_flags.models import FeatureFlagOverride
from backend.app.models.core import Project


def _active_clause():
    """SQL clause: override aún activo (no revocado, no expired, no purged)."""
    now = datetime.now(timezone.utc)
    return and_(
        FeatureFlagOverride.revoked_at.is_(None),
        FeatureFlagOverride.deleted_at.is_(None),
        or_(
            FeatureFlagOverride.expires_at.is_(None),
            FeatureFlagOverride.expires_at > now,
        ),
    )


async def _fetch_active_overrides_for_project(
    db: AsyncSession,
    project: Project,
) -> dict[str, Any]:
    """Devuelve dict ``{feature_key: override_value}`` activos para project.

    Resuelve project-level y client-level. Project-level wins ante empate
    misma key (más específico).
    """
    project_stmt = select(FeatureFlagOverride).where(
        FeatureFlagOverride.project_id == project.id,
        _active_clause(),
    )
    client_stmt = select(FeatureFlagOverride).where(
        FeatureFlagOverride.client_id == project.client_id,
        FeatureFlagOverride.project_id.is_(None),
        _active_clause(),
    )

    project_rows = (await db.execute(project_stmt)).scalars().all()
    client_rows = (await db.execute(client_stmt)).scalars().all()

    merged: dict[str, Any] = {}
    for row in client_rows:
        merged[row.feature_key] = row.override_value
    for row in project_rows:
        merged[row.feature_key] = row.override_value
    return merged


async def resolve_project_features(
    db: AsyncSession,
    project: Project,
) -> dict[str, Any]:
    """Dict ``{feature_key: value}`` con YAML + overrides merged.

    Reemplaza ``get_features_for_project()`` cuando hay un Project DB
    cargado (necesario para project_id/client_id lookup).
    """
    employee_count = (
        project.client.numero_empleados if project.client else None
    )
    yaml_eval = get_features_for_project(
        categoria=project.categoria_objetivo or "BASICA",
        archetype=project.archetype,
        employee_count=employee_count,
    )
    overrides = await _fetch_active_overrides_for_project(db, project)
    return {**yaml_eval, **overrides}


async def grant_override(
    db: AsyncSession,
    *,
    feature_key: str,
    override_value: Any,
    granted_by_user_id: UUID | None,
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    expires_at: datetime | None = None,
    reason: str | None = None,
) -> FeatureFlagOverride:
    """Crea row override. Caller debe pasar project_id O client_id (al menos uno).

    DB CHECK ``ck_feature_flag_overrides_scope_required`` valida defensivo.
    """
    if project_id is None and client_id is None:
        raise ValueError(
            "grant_override requires project_id OR client_id (al menos uno)"
        )
    override = FeatureFlagOverride(
        project_id=project_id,
        client_id=client_id,
        feature_key=feature_key,
        override_value=override_value,
        granted_by_user_id=granted_by_user_id,
        expires_at=expires_at,
        reason=reason,
    )
    db.add(override)
    await db.flush()
    await db.refresh(override)
    return override


async def revoke_override(
    db: AsyncSession,
    *,
    override_id: UUID,
    revoked_by_user_id: UUID,
    reason: str | None = None,
) -> FeatureFlagOverride | None:
    """Marca override como revoked. Retorna None si no existe o ya revocado."""
    stmt = select(FeatureFlagOverride).where(
        FeatureFlagOverride.id == override_id,
        FeatureFlagOverride.revoked_at.is_(None),
        FeatureFlagOverride.deleted_at.is_(None),
    )
    override = (await db.execute(stmt)).scalar_one_or_none()
    if override is None:
        return None
    override.revoked_at = datetime.now(timezone.utc)
    override.revoked_by_user_id = revoked_by_user_id
    if reason is not None:
        override.reason = reason
    await db.flush()
    await db.refresh(override)
    return override


async def list_overrides(
    db: AsyncSession,
    *,
    project_id: UUID | None = None,
    client_id: UUID | None = None,
    include_revoked: bool = False,
) -> list[FeatureFlagOverride]:
    """Lista overrides per scope. Si include_revoked=False filtra activos."""
    if project_id is None and client_id is None:
        raise ValueError(
            "list_overrides requires project_id OR client_id"
        )
    filters = []
    if project_id is not None:
        filters.append(FeatureFlagOverride.project_id == project_id)
    if client_id is not None:
        filters.append(FeatureFlagOverride.client_id == client_id)
    where_clause = or_(*filters) if len(filters) > 1 else filters[0]

    stmt = select(FeatureFlagOverride).where(
        where_clause,
        FeatureFlagOverride.deleted_at.is_(None),
    )
    if not include_revoked:
        stmt = stmt.where(FeatureFlagOverride.revoked_at.is_(None))
    stmt = stmt.order_by(FeatureFlagOverride.granted_at.desc())
    return list((await db.execute(stmt)).scalars().all())
