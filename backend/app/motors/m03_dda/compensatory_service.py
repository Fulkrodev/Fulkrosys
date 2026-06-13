"""Servicio de medidas compensatorias tipadas (RD 311/2022 Art. 8).

feat/fulkro-100 Ola D. CRUD + workflow de aprobación de la medida compensatoria.
Determinista (R1). NO muta la ``dda_entries`` enlazada (evita corromper una DdA
ya firmada); el valor COMPENSADA del enum Aplicabilidad queda disponible para que
el admin lo aplique a la entrada por la vía normal cuando proceda.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.compensatory_control import (
    COMPENSATORY_STATES,
    CompensatoryControl,
)


class CompensatoryError(ValueError):
    """Error de validación de medida compensatoria."""


async def create_compensatory(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_code: str,
    motivo_no_aplica_directa: str,
    control_compensatorio: str,
    riesgo_residual: Optional[str] = None,
    dda_entry_id: Optional[uuid.UUID] = None,
    observaciones: Optional[str] = None,
) -> CompensatoryControl:
    """Crea una medida compensatoria (estado inicial pendiente_aprobacion)."""
    row = CompensatoryControl(
        project_id=project_id,
        dda_entry_id=dda_entry_id,
        measure_code=measure_code,
        motivo_no_aplica_directa=motivo_no_aplica_directa,
        control_compensatorio=control_compensatorio,
        riesgo_residual=riesgo_residual,
        estado="pendiente_aprobacion",
        observaciones=observaciones,
    )
    db.add(row)
    await db.flush()
    return row


async def list_compensatory(
    db: AsyncSession, *, project_id: uuid.UUID,
) -> list[CompensatoryControl]:
    return list((await db.execute(
        select(CompensatoryControl)
        .where(
            CompensatoryControl.project_id == project_id,
            CompensatoryControl.deleted_at.is_(None),
        )
        .order_by(CompensatoryControl.created_at.desc())
    )).scalars().all())


async def get_compensatory(
    db: AsyncSession, *, cc_id: uuid.UUID,
) -> Optional[CompensatoryControl]:
    row = await db.get(CompensatoryControl, cc_id)
    if row is None or row.deleted_at is not None:
        return None
    return row


async def decide_compensatory(
    db: AsyncSession,
    *,
    cc_id: uuid.UUID,
    aprobada: bool,
    aprobado_por: str,
    observaciones: Optional[str] = None,
) -> Optional[CompensatoryControl]:
    """Aprueba o rechaza la medida (la Dirección decide · Art. 8).

    estado → aprobada | rechazada + aprobado_por + fecha_aprobacion.
    """
    row = await get_compensatory(db, cc_id=cc_id)
    if row is None:
        return None
    if not (aprobado_por or "").strip():
        raise CompensatoryError("aprobado_por es obligatorio para decidir")
    row.estado = "aprobada" if aprobada else "rechazada"
    row.aprobado_por = aprobado_por.strip()
    row.fecha_aprobacion = datetime.now(timezone.utc).date()
    if observaciones is not None:
        row.observaciones = observaciones
    assert row.estado in COMPENSATORY_STATES
    await db.flush()
    return row
