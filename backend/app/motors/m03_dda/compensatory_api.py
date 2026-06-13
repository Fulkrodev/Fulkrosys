"""API admin de medidas compensatorias tipadas (RD 311/2022 Art. 8).

feat/fulkro-100 Ola D. Marcos (require_owner) documenta y la Dirección aprueba las
medidas compensatorias. ADR-013 doble pool · audit_log Sub-atom 5.A.
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.compensatory_control import CompensatoryControl
from backend.app.models.core import Project
from backend.app.motors.m03_dda.compensatory_service import (
    CompensatoryError,
    create_compensatory,
    decide_compensatory,
    get_compensatory,
    list_compensatory,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dda",
    tags=["Motor 3 - DdA · Compensatorias (Art. 8)"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class CompensatoryCreate(BaseModel):
    measure_code: str = Field(..., min_length=1, max_length=30)
    motivo_no_aplica_directa: str = Field(..., min_length=1, max_length=10000)
    control_compensatorio: str = Field(..., min_length=1, max_length=10000)
    riesgo_residual: Optional[str] = Field(None, max_length=10000)
    dda_entry_id: Optional[uuid.UUID] = None
    observaciones: Optional[str] = Field(None, max_length=10000)


class CompensatoryDecision(BaseModel):
    aprobada: bool
    aprobado_por: str = Field(..., min_length=1, max_length=255)
    observaciones: Optional[str] = Field(None, max_length=10000)


class CompensatoryOut(BaseModel):
    id: str
    project_id: str
    dda_entry_id: Optional[str] = None
    measure_code: str
    motivo_no_aplica_directa: str
    control_compensatorio: str
    riesgo_residual: Optional[str] = None
    estado: str
    aprobado_por: Optional[str] = None
    fecha_aprobacion: Optional[str] = None
    observaciones: Optional[str] = None
    created_at: Optional[str] = None


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _to_out(r: CompensatoryControl) -> CompensatoryOut:
    return CompensatoryOut(
        id=str(r.id),
        project_id=str(r.project_id),
        dda_entry_id=str(r.dda_entry_id) if r.dda_entry_id else None,
        measure_code=r.measure_code,
        motivo_no_aplica_directa=r.motivo_no_aplica_directa,
        control_compensatorio=r.control_compensatorio,
        riesgo_residual=r.riesgo_residual,
        estado=r.estado,
        aprobado_por=r.aprobado_por,
        fecha_aprobacion=(
            r.fecha_aprobacion.isoformat() if r.fecha_aprobacion else None
        ),
        observaciones=r.observaciones,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


async def _ensure_project_rls(db: AsyncSession, project_id: uuid.UUID) -> str:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    client_id = str(project.client_id)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )
    return client_id


async def _emit_audit(
    db: AsyncSession, *, project_id: str, client_id: str,
    accion: str, usuario: str, registro_id: str, payload: Optional[dict] = None,
) -> None:
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'compensatory_controls', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": registro_id, "accion": accion, "usuario": usuario,
                "pid": project_id, "cid": client_id,
                "payload": _json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log %s emit failed · pid=%s", accion, project_id)


# ════════════════════════════════════════════════════════════════════
# Endpoints (project-scoped)
# ════════════════════════════════════════════════════════════════════

_P = "/projects/{project_id}/compensatory-controls"


@router.post(_P, response_model=CompensatoryOut, status_code=201)
async def create_control(
    project_id: uuid.UUID,
    body: CompensatoryCreate,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> CompensatoryOut:
    """Documenta una medida compensatoria (pendiente de aprobación)."""
    client_id = await _ensure_project_rls(db, project_id)
    try:
        row = await create_compensatory(
            db,
            project_id=project_id,
            measure_code=body.measure_code,
            motivo_no_aplica_directa=body.motivo_no_aplica_directa,
            control_compensatorio=body.control_compensatorio,
            riesgo_residual=body.riesgo_residual,
            dda_entry_id=body.dda_entry_id,
            observaciones=body.observaciones,
        )
        await _emit_audit(
            db, project_id=str(project_id), client_id=client_id,
            accion="compensatory.created",
            usuario=getattr(owner, "email", "admin") or "admin",
            registro_id=str(row.id), payload={"measure_code": body.measure_code},
        )
        await db.commit()
    except CompensatoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_out(row)


@router.get(_P, response_model=list[CompensatoryOut])
async def list_controls(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CompensatoryOut]:
    await _ensure_project_rls(db, project_id)
    rows = await list_compensatory(db, project_id=project_id)
    return [_to_out(r) for r in rows]


@router.get(f"{_P}/{{cc_id}}", response_model=CompensatoryOut)
async def get_control(
    project_id: uuid.UUID,
    cc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CompensatoryOut:
    await _ensure_project_rls(db, project_id)
    row = await get_compensatory(db, cc_id=cc_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Compensatoria no encontrada")
    return _to_out(row)


@router.post(f"{_P}/{{cc_id}}/approve", response_model=CompensatoryOut)
async def decide_control(
    project_id: uuid.UUID,
    cc_id: uuid.UUID,
    body: CompensatoryDecision,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> CompensatoryOut:
    """La Dirección aprueba o rechaza la medida compensatoria (Art. 8)."""
    client_id = await _ensure_project_rls(db, project_id)
    existing = await get_compensatory(db, cc_id=cc_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Compensatoria no encontrada")
    try:
        row = await decide_compensatory(
            db, cc_id=cc_id, aprobada=body.aprobada,
            aprobado_por=body.aprobado_por, observaciones=body.observaciones,
        )
    except CompensatoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    assert row is not None
    await _emit_audit(
        db, project_id=str(project_id), client_id=client_id,
        accion="compensatory.decided",
        usuario=getattr(owner, "email", "admin") or "admin",
        registro_id=str(cc_id), payload={"estado": row.estado},
    )
    await db.commit()
    return _to_out(row)
