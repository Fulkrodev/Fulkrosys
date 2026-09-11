"""Cual es el analisis MAGERIT vigente de un proyecto · fuente unica.

La pregunta "¿que analisis de riesgos tiene este proyecto?" estaba respondida
CUATRO veces con cuatro trozos de codigo distintos:

- ``m22_discovery/paso6_asset_discoverer._get_or_create_magerit_analysis``
- ``m02_magerit/portal_api._get_active_analysis_id``
- ``m02_magerit/portal_api.magerit_summary`` (copia en linea de la anterior)
- ``core/workflow_gates.require_magerit_analysis`` (un COUNT, no un SELECT)

Cuatro copias de una regla es cuatro sitios donde diverge. Aqui se escribe
una vez y los cuatro la llaman.

REGLA · el analisis vigente de un proyecto es el ultimo no borrado, por
``created_at`` descendente. El desempate por ``id`` no estaba antes: cuando dos
analisis comparten el mismo ``created_at`` -- que ocurre, porque
``server_default now()`` da el mismo sello a todo lo insertado en la misma
transaccion (OPS-047) -- el ganador lo elegia el planificador, asi que dos
llamadas seguidas podian responder cosas distintas. Con el desempate la
respuesta es siempre la misma.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m02_magerit.models import MageritAnalysis


async def analisis_vigente(
    db: AsyncSession, project_id: uuid.UUID,
) -> MageritAnalysis | None:
    """El analisis MAGERIT vigente del proyecto, o ``None`` si no hay ninguno.

    No crea nada y no lanza: quien necesite exigir su existencia lo comprueba
    contra ``None`` (asi lo hace la puerta de ``workflow_gates``).
    """
    row = await db.execute(
        select(MageritAnalysis)
        .where(MageritAnalysis.project_id == project_id)
        .where(MageritAnalysis.deleted_at.is_(None))
        .order_by(
            MageritAnalysis.created_at.desc(),
            MageritAnalysis.id.desc(),
        )
        .limit(1)
    )
    return row.scalar_one_or_none()


async def id_analisis_vigente(
    db: AsyncSession, project_id: uuid.UUID,
) -> uuid.UUID | None:
    """Solo el id del analisis vigente · azucar para los llamantes que no
    necesitan la fila entera."""
    analisis = await analisis_vigente(db, project_id)
    return analisis.id if analisis is not None else None
