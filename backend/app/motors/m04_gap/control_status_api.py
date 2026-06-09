"""Control Status API · CLUSTER 3 Phase 3B endpoints.

Filosofía cliente-mínimo:
- Admin endpoints (require_owner · ADR-013): full ControlStatusResult con
  technical detail · missing_reasons admin technical
- Cliente endpoint (require_client_user · ADR-013 doble pool): R29 friendly
  version · cliente-friendly missing_reasons translation · NO admin lingo

audit_log Sub-atom 5.A 3-way OR · ENAC trazabilidad.
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m04_gap.control_status_service import (
    compute_control_status,
    translate_missing_reasons_cliente_friendly,
)
from backend.app.motors.m04_gap.service import get_measure_cmm_detail
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ControlStatusResponse(BaseModel):
    control_id: Optional[uuid.UUID] = None
    measure_code: Optional[str] = None
    semaforo: str
    documents_count: int
    documents_approved_count: int
    documents_signed_count: int
    cliente_reviewed_count: int
    expired_count: int
    missing_reasons: list[str]
    requirements_met: dict[str, bool]


class MeasureCmmResponse(BaseModel):
    """#21 cierre · lente MADUREZ (CMM) de una medida para la fila SoA."""

    measure_code: str
    estado_implementacion: Optional[str] = None  # lente conformidad (declarado)
    cmm_level: Optional[str] = None              # L0-L4 derivado (None si no_aplica)
    cmm_label: Optional[str] = None              # etiqueta legible CCN-STIC 804
    target_level: Optional[str] = None           # objetivo por categoría


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _resolve_client_id_from_project(
    db: AsyncSession, project_id: str,
) -> Optional[str]:
    row = (await db.execute(
        text(
            "SELECT client_id FROM projects "
            "WHERE id = :pid AND deleted_at IS NULL"
        ),
        {"pid": project_id},
    )).first()
    return str(row[0]) if row else None


async def _set_admin_rls(db: AsyncSession, project_id: str) -> None:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )


async def _set_cliente_rls(
    db: AsyncSession, *, project_id: str, client_id: str,
) -> None:
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )


async def _resolve_cliente_project(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[tuple[str, str]]:
    row = (await db.execute(
        text(
            "SELECT id, client_id FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )).first()
    return (str(row[0]), str(row[1])) if row else None


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: Optional[str],
    accion: str,
    payload: Optional[dict] = None,
    usuario: str = "system",
) -> None:
    """Sub-atom 5.A 3-way OR audit_log emit · best-effort try/except."""
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'control_status', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": str(uuid.uuid4()),
                "accion": accion,
                "usuario": usuario[:255],
                "pid": project_id,
                "cid": client_id,
                "payload": _json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log %s emit failed", accion)


# ════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════


router_admin = APIRouter(
    prefix="/admin/projects",
    tags=["Admin · Control Status (M04 · CLUSTER 3 Phase 3B)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.get(
    "/{project_id}/controls/status", response_model=ControlStatusResponse,
)
async def admin_get_control_status(
    project_id: uuid.UUID,
    control_id: Optional[uuid.UUID] = None,
    measure_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """Admin compute control status canonical · full detail.

    Query at least ONE of: control_id OR measure_code.
    Returns ControlStatusResult deterministic con missing_reasons admin technical.
    """
    if control_id is None and measure_code is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of: control_id, measure_code required",
        )

    await _set_admin_rls(db, str(project_id))
    client_id = await _resolve_client_id_from_project(db, str(project_id))

    result = await compute_control_status(
        db,
        project_id=project_id,
        control_id=control_id,
        measure_code=measure_code,
    )

    await _emit_audit_log(
        db,
        project_id=str(project_id),
        client_id=client_id,
        accion="admin.control.status.viewed",
        usuario=str(user.id),
        payload={
            "control_id": str(control_id) if control_id else None,
            "measure_code": measure_code,
            "semaforo": result.semaforo,
        },
    )
    await db.commit()

    return ControlStatusResponse(**result.to_dict())


@router_admin.get(
    "/{project_id}/controls/cmm", response_model=MeasureCmmResponse,
)
async def admin_get_measure_cmm(
    project_id: uuid.UUID,
    measure_code: str,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """#21 cierre · lente MADUREZ (CMM) de una medida (admin · require_owner).

    Deriva el nivel CMM de la SoA (estado_implementacion) + acople L4 (evidencia
    verde). Tercera lente de la fila SoA junto a estado_implementacion (declarado)
    y el semáforo (evidencia en regla)."""
    await _set_admin_rls(db, str(project_id))
    detail = await get_measure_cmm_detail(
        db, project_id=project_id, measure_code=measure_code,
    )
    return MeasureCmmResponse(**detail)


# ════════════════════════════════════════════════════════════════════
# Cliente router (require_client_user · ADR-013 doble pool)
# ════════════════════════════════════════════════════════════════════


router_cliente = APIRouter(
    prefix="/client-portal/controls",
    tags=["Portal Cliente · Control Status (CLUSTER 3 Phase 3B)"],
)


@router_cliente.get("/status", response_model=ControlStatusResponse)
async def cliente_get_control_status(
    control_id: Optional[uuid.UUID] = None,
    measure_code: Optional[str] = None,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente views control status · R29 friendly missing_reasons.

    Query at least ONE of: control_id OR measure_code.
    Returns ControlStatusResult con missing_reasons cliente-friendly.
    """
    if control_id is None and measure_code is None:
        raise HTTPException(
            status_code=400,
            detail="Necesitas indicar el control o la medida.",
        )

    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await _set_cliente_rls(db, project_id=project_id_str, client_id=client_id_str)

    result = await compute_control_status(
        db,
        project_id=uuid.UUID(project_id_str),
        control_id=control_id,
        measure_code=measure_code,
    )

    # R29 friendly translation
    friendly_reasons = translate_missing_reasons_cliente_friendly(
        result.missing_reasons,
    )

    response_data = result.to_dict()
    response_data["missing_reasons"] = friendly_reasons

    await _emit_audit_log(
        db,
        project_id=project_id_str,
        client_id=client_id_str,
        accion="cliente.control.status.viewed",
        usuario=str(user.id),
        payload={
            "control_id": str(control_id) if control_id else None,
            "measure_code": measure_code,
            "semaforo": result.semaforo,
        },
    )
    await db.commit()

    return ControlStatusResponse(**response_data)


@router_cliente.get("/cmm", response_model=MeasureCmmResponse)
async def cliente_get_measure_cmm(
    measure_code: str,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """#21 cierre · lente MADUREZ (CMM) de una medida (cliente · ADR-013 doble
    pool · proyecto resuelto de sesión)."""
    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await _set_cliente_rls(db, project_id=project_id_str, client_id=client_id_str)
    detail = await get_measure_cmm_detail(
        db, project_id=uuid.UUID(project_id_str), measure_code=measure_code,
    )
    return MeasureCmmResponse(**detail)
