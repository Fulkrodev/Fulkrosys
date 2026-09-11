"""Cual es el analisis MAGERIT vigente de un proyecto · fuente unica.

La pregunta "¿que analisis de riesgos tiene este proyecto?" estaba respondida
CUATRO veces con cuatro trozos de codigo distintos:

- ``m22_discovery/paso6_asset_discoverer._get_or_create_magerit_analysis``
- ``m02_magerit/portal_api._get_active_analysis_id``
- ``m02_magerit/portal_api.magerit_summary`` (copia en linea de la anterior)
- ``core/workflow_gates.require_magerit_analysis`` (un COUNT, no un SELECT)

Cuatro copias de una regla es cuatro sitios donde diverge. Aqui se escribe
una vez y los cuatro la llaman.

REGLA · el analisis vigente es el que lleva la marca ``es_vigente``. No se
ordena por nada: ordenar era justo el problema.

    Antes la regla era "el ultimo no borrado por ``created_at`` descendente",
    sin desempate. Y ``created_at`` lleva ``server_default now()``, que en
    PostgreSQL devuelve el sello de INICIO DE TRANSACCION: dos analisis creados
    en la misma transaccion comparten ``created_at`` al microsegundo, y entonces
    el "ultimo" lo elige el planificador de consultas. De ese analisis cuelga el
    informe E-028, que se firma.

    La marca la mantienen dos disparadores y la protege un indice unico parcial
    (migracion ``magerit_analisis_vigente_001``), asi que la garantia no depende
    de que los llamantes usen este modulo: el noveno que escriba la consulta a
    mano se encontrara con que no hay nada que ordenar.
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
        .where(MageritAnalysis.es_vigente.is_(True))
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
