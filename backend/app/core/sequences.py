"""Generadores de secuencias de negocio serializadas (FIX P1-8).

Patrón #22 (advisory lock por recurso) para numeraciones correlativas que tienen
MÁS DE UN generador concurrente y por tanto no pueden depender de COUNT(*)+1 sin
serializar.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


async def next_change_request_code(
    db: AsyncSession, project_id: uuid.UUID,
) -> str:
    """Siguiente código ``CR-NNN`` por proyecto, SERIALIZADO.

    FIX P1-8: existían DOS generadores (m17 planning_service ``COUNT(*)+1`` y
    m19_risk ``len(list)+1``) que, bajo concurrencia, producían el mismo
    ``CR-NNN`` (sin lock ni unique). ``pg_advisory_xact_lock`` por ``project_id``
    los serializa (el lock se libera al commit/rollback); la unicidad
    ``(project_id, code)`` en BD (migración ``change_request_code_unique_001``) es
    la red de seguridad: una colisión residual falla ruidoso en vez de duplicar.
    """
    from backend.app.models.planning import ChangeRequest

    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"change_request_{project_id}"},
    )
    count = (await db.execute(
        select(func.count(ChangeRequest.id)).where(
            ChangeRequest.project_id == project_id,
        )
    )).scalar_one() or 0
    return f"CR-{count + 1:03d}"
