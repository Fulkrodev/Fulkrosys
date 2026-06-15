"""API admin de registros de pruebas de continuidad (op.cont.3).

feat/fulkro-100 Ola D. Marcos (require_owner) registra y consulta las pruebas
periódicas del plan de continuidad. ADR-013 doble pool · audit_log Sub-atom 5.A.
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.continuity_test_execution import ContinuityTestExecution
from backend.app.motors.m19_risk.continuity_test_execution_service import (
    InvalidResultadoError,
    aggregate_test_history,
    create_execution,
    get_execution,
    list_executions,
    update_execution,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/projects",
    tags=["M19 - Continuidad (op.cont.3 pruebas)"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ContinuityTestCreate(BaseModel):
    fecha_prueba: datetime
    escenario: str = Field(..., min_length=1, max_length=255)
    resultado: str = Field(..., pattern="^(pass|parcial|fail)$")
    hallazgos: Optional[str] = Field(None, max_length=10000)
    proxima_prueba_due: Optional[date] = None
    evidencia_ref: Optional[str] = Field(None, max_length=500)


class ContinuityTestUpdate(BaseModel):
    escenario: Optional[str] = Field(None, min_length=1, max_length=255)
    resultado: Optional[str] = Field(None, pattern="^(pass|parcial|fail)$")
    hallazgos: Optional[str] = Field(None, max_length=10000)
    proxima_prueba_due: Optional[date] = None
    evidencia_ref: Optional[str] = Field(None, max_length=500)


class ContinuityTestOut(BaseModel):
    id: str
    project_id: str
    fecha_prueba: str
    escenario: str
    resultado: str
    hallazgos: Optional[str] = None
    proxima_prueba_due: Optional[str] = None
    evidencia_ref: Optional[str] = None
    created_at: Optional[str] = None


class ContinuityTestHistory(BaseModel):
    total_pruebas: int
    pass_rate: Optional[int] = None
    ultima_prueba: Optional[str] = None
    ultimo_resultado: Optional[str] = None
    proxima_prueba_due: Optional[str] = None


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _to_out(r: ContinuityTestExecution) -> ContinuityTestOut:
    return ContinuityTestOut(
        id=str(r.id),
        project_id=str(r.project_id),
        fecha_prueba=r.fecha_prueba.isoformat(),
        escenario=r.escenario,
        resultado=r.resultado,
        hallazgos=r.hallazgos,
        proxima_prueba_due=(
            r.proxima_prueba_due.isoformat() if r.proxima_prueba_due else None
        ),
        evidencia_ref=r.evidencia_ref,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


async def _ensure_project_rls(
    db: AsyncSession, project_id: uuid.UUID,
) -> str:
    """Verifica proyecto + setea contexto RLS · devuelve client_id.

    Usa get_project_owner (SECURITY DEFINER) para resolver el owner SIN RLS:
    antes `db.get(Project)` corría bajo fulkro_app sin contexto de tenant aún
    fijado (chicken-and-egg) → devolvía None y 404 espurio para proyectos válidos.
    """
    owner = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not owner:
        raise HTTPException(status_code=404, detail="Project not found")
    client_id = str(owner)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": client_id},
    )
    return client_id


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: str,
    accion: str,
    usuario: str,
    registro_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """audit_log Sub-atom 5.A 3-way OR · best-effort."""
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'continuity_test_executions', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": registro_id or str(uuid.uuid4()),
                "accion": accion,
                "usuario": usuario,
                "pid": project_id,
                "cid": client_id,
                "payload": _json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception("audit_log %s emit failed · pid=%s", accion, project_id)


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════

_PREFIX = "/{project_id}/continuity-tests"


@router.post(
    f"{_PREFIX}/executions",
    response_model=ContinuityTestOut, status_code=201,
)
async def create_test(
    project_id: uuid.UUID,
    body: ContinuityTestCreate,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> ContinuityTestOut:
    """Registra una ejecución de prueba de continuidad (op.cont.3)."""
    client_id = await _ensure_project_rls(db, project_id)
    try:
        row = await create_execution(
            db,
            project_id=project_id,
            fecha_prueba=body.fecha_prueba,
            escenario=body.escenario,
            resultado=body.resultado,
            hallazgos=body.hallazgos,
            proxima_prueba_due=body.proxima_prueba_due,
            evidencia_ref=body.evidencia_ref,
        )
    except InvalidResultadoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await _emit_audit_log(
        db, project_id=str(project_id), client_id=client_id,
        accion="continuity_test.recorded", usuario=getattr(owner, "email", "admin") or "admin",
        registro_id=str(row.id), payload={"resultado": body.resultado},
    )
    await db.commit()
    return _to_out(row)


@router.get(f"{_PREFIX}/executions", response_model=list[ContinuityTestOut])
async def list_tests(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ContinuityTestOut]:
    """Lista las pruebas del proyecto (más reciente primero)."""
    await _ensure_project_rls(db, project_id)
    rows = await list_executions(db, project_id=project_id)
    return [_to_out(r) for r in rows]


@router.get(f"{_PREFIX}/history", response_model=ContinuityTestHistory)
async def get_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContinuityTestHistory:
    """Resumen del historial de pruebas (total · % pass · próxima vencida)."""
    await _ensure_project_rls(db, project_id)
    return ContinuityTestHistory(**await aggregate_test_history(db, project_id=project_id))


@router.get(
    f"{_PREFIX}/executions/{{execution_id}}",
    response_model=ContinuityTestOut,
)
async def get_test(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContinuityTestOut:
    await _ensure_project_rls(db, project_id)
    row = await get_execution(db, execution_id=execution_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="Prueba no encontrada")
    return _to_out(row)


@router.patch(
    f"{_PREFIX}/executions/{{execution_id}}",
    response_model=ContinuityTestOut,
)
async def patch_test(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    body: ContinuityTestUpdate,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> ContinuityTestOut:
    client_id = await _ensure_project_rls(db, project_id)
    existing = await get_execution(db, execution_id=execution_id)
    if existing is None or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Prueba no encontrada")
    try:
        row = await update_execution(
            db,
            execution_id=execution_id,
            escenario=body.escenario,
            resultado=body.resultado,
            hallazgos=body.hallazgos,
            proxima_prueba_due=body.proxima_prueba_due,
            evidencia_ref=body.evidencia_ref,
        )
    except InvalidResultadoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await _emit_audit_log(
        db, project_id=str(project_id), client_id=client_id,
        accion="continuity_test.updated", usuario=getattr(owner, "email", "admin") or "admin",
        registro_id=str(execution_id),
    )
    await db.commit()
    assert row is not None
    return _to_out(row)
