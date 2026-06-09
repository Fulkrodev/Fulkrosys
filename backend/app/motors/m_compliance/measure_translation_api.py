"""Measure Translation API · CLUSTER 3 Phase 3C gap translation layer endpoints.

Filosofía cliente-mínimo:
- Admin endpoint (require_owner · ADR-013): full MeasureTranslation (technical
  detail + cliente friendly)
- Cliente endpoint (require_client_user · ADR-013 doble pool): cliente-friendly
  only · R29 firmísimo · NO admin lingo leak

audit_log Sub-atom 5.A 3-way OR · ENAC trazabilidad cliente views.
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
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m_compliance.measure_translation_service import (
    translate_measure_to_cliente_friendly,
)


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class MeasureTranslationAdminResponse(BaseModel):
    measure_code: str
    nombre: str
    cliente_friendly_title: str
    cliente_friendly_explanation: str
    admin_technical_detail: str
    familia: Optional[str] = None
    categoria_minima: Optional[str] = None
    fuente_oficial: Optional[str] = None
    has_curated_override: bool


class MeasureTranslationClienteResponse(BaseModel):
    """Cliente endpoint response · R29 firmísimo NO admin_technical_detail."""
    measure_code: str
    cliente_friendly_title: str
    cliente_friendly_explanation: str
    categoria_minima: Optional[str] = None


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


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


async def _emit_audit_log_cliente(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: str,
    measure_code: str,
    usuario: str,
) -> None:
    """Sub-atom 5.A 3-way OR audit_log emit · cliente.measure.translation.viewed."""
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'measure_translation', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": str(uuid.uuid4()),
                "accion": "cliente.measure.translation.viewed",
                "usuario": usuario[:255],
                "pid": project_id,
                "cid": client_id,
                "payload": _json.dumps({"measure_code": measure_code}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "audit_log cliente.measure.translation.viewed emit failed · "
            "measure_code=%s",
            measure_code,
        )


# ════════════════════════════════════════════════════════════════════
# Admin router (require_owner)
# ════════════════════════════════════════════════════════════════════


router_admin = APIRouter(
    prefix="/admin/measures",
    tags=["Admin · Measure Translation (m_compliance · CLUSTER 3 Phase 3C)"],
    dependencies=[Depends(require_owner)],
)


@router_admin.get(
    "/{measure_code}/translation",
    response_model=MeasureTranslationAdminResponse,
)
async def admin_get_measure_translation(
    measure_code: str,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_owner),
):
    """Admin GET full MeasureTranslation · technical + cliente friendly."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    translation = await translate_measure_to_cliente_friendly(db, measure_code)
    if translation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Measure code '{measure_code}' not found in ens_measures",
        )

    return MeasureTranslationAdminResponse(**translation.to_admin_dict())


# ════════════════════════════════════════════════════════════════════
# Cliente router (require_client_user · ADR-013 doble pool · R29)
# ════════════════════════════════════════════════════════════════════


router_cliente = APIRouter(
    prefix="/client-portal/measures",
    tags=["Portal Cliente · Measure Translation (CLUSTER 3 Phase 3C)"],
)


@router_cliente.get(
    "/{measure_code}/explain",
    response_model=MeasureTranslationClienteResponse,
)
async def cliente_get_measure_explanation(
    measure_code: str,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente GET cliente-friendly explanation · R29 firmísimo.

    NO admin_technical_detail leak (filosofía cliente-mínimo enforcement).
    audit_log emit cliente.measure.translation.viewed Sub-atom 5.A 3-way OR.
    """
    proj = await _resolve_cliente_project(db, user.client_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Sin proyecto activo")
    project_id_str, client_id_str = proj
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id_str},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id_str},
    )

    translation = await translate_measure_to_cliente_friendly(db, measure_code)
    if translation is None:
        raise HTTPException(
            status_code=404,
            detail="No tenemos información para esta referencia",
        )

    await _emit_audit_log_cliente(
        db,
        project_id=project_id_str,
        client_id=client_id_str,
        measure_code=measure_code,
        usuario=str(user.id),
    )
    await db.commit()

    return MeasureTranslationClienteResponse(**translation.to_cliente_dict())
