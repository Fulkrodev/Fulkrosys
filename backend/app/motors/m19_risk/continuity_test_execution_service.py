"""Servicio de registros de pruebas de continuidad (op.cont.3).

feat/fulkro-100 Ola D. CRUD + agregado de historial de las pruebas periódicas
del plan de continuidad. Determinista (R1 · sin LLM). Operación admin.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.continuity_test_execution import (
    CONTINUITY_TEST_RESULTS,
    ContinuityTestExecution,
)


class InvalidResultadoError(ValueError):
    """resultado fuera del enum permitido (pass/parcial/fail)."""


def _validate_resultado(resultado: str) -> None:
    if resultado not in CONTINUITY_TEST_RESULTS:
        raise InvalidResultadoError(
            f"resultado inválido: {resultado!r} · "
            f"válidos: {list(CONTINUITY_TEST_RESULTS)}"
        )


async def create_execution(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    fecha_prueba: datetime,
    escenario: str,
    resultado: str,
    hallazgos: Optional[str] = None,
    proxima_prueba_due: Optional[date] = None,
    evidencia_ref: Optional[str] = None,
) -> ContinuityTestExecution:
    """Crea un registro de ejecución de prueba de continuidad."""
    _validate_resultado(resultado)
    row = ContinuityTestExecution(
        project_id=project_id,
        fecha_prueba=fecha_prueba,
        escenario=escenario,
        resultado=resultado,
        hallazgos=hallazgos,
        proxima_prueba_due=proxima_prueba_due,
        evidencia_ref=evidencia_ref,
    )
    db.add(row)
    await db.flush()
    return row


async def list_executions(
    db: AsyncSession, *, project_id: uuid.UUID,
) -> list[ContinuityTestExecution]:
    """Lista las pruebas del proyecto · más reciente primero."""
    return list((await db.execute(
        select(ContinuityTestExecution)
        .where(
            ContinuityTestExecution.project_id == project_id,
            ContinuityTestExecution.deleted_at.is_(None),
        )
        .order_by(ContinuityTestExecution.fecha_prueba.desc())
    )).scalars().all())


async def get_execution(
    db: AsyncSession, *, execution_id: uuid.UUID,
) -> Optional[ContinuityTestExecution]:
    row = await db.get(ContinuityTestExecution, execution_id)
    if row is None or row.deleted_at is not None:
        return None
    return row


async def update_execution(
    db: AsyncSession,
    *,
    execution_id: uuid.UUID,
    escenario: Optional[str] = None,
    resultado: Optional[str] = None,
    hallazgos: Optional[str] = None,
    proxima_prueba_due: Optional[date] = None,
    evidencia_ref: Optional[str] = None,
) -> Optional[ContinuityTestExecution]:
    """Actualiza campos editables de una prueba (None = no tocar)."""
    row = await get_execution(db, execution_id=execution_id)
    if row is None:
        return None
    if resultado is not None:
        _validate_resultado(resultado)
        row.resultado = resultado
    if escenario is not None:
        row.escenario = escenario
    if hallazgos is not None:
        row.hallazgos = hallazgos
    if proxima_prueba_due is not None:
        row.proxima_prueba_due = proxima_prueba_due
    if evidencia_ref is not None:
        row.evidencia_ref = evidencia_ref
    await db.flush()
    return row


async def aggregate_test_history(
    db: AsyncSession, *, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Resumen del historial: total, % pass, última prueba, próxima vencida.

    op.cont.3 pide pruebas PERIÓDICAS · este agregado alimenta el panel admin
    y futuras alertas de "próxima prueba vencida".
    """
    rows = await list_executions(db, project_id=project_id)
    total = len(rows)
    passed = sum(1 for r in rows if r.resultado == "pass")
    last = rows[0] if rows else None
    # Próxima prueba pendiente más cercana en el futuro (o ya vencida).
    due_dates = [r.proxima_prueba_due for r in rows if r.proxima_prueba_due]
    next_due = min(due_dates) if due_dates else None
    return {
        "total_pruebas": total,
        "pass_rate": round(100 * passed / total) if total else None,
        "ultima_prueba": last.fecha_prueba.isoformat() if last else None,
        "ultimo_resultado": last.resultado if last else None,
        "proxima_prueba_due": next_due.isoformat() if next_due else None,
    }
