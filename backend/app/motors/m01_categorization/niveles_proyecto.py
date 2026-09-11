"""El nivel de cada dimension de un PROYECTO · una sola lectura.

La consulta -- el maximo por dimension sobre los tipos de informacion y los
servicios de todos los sistemas del proyecto, arrancando en NO_AFECTADA -- se
escribio para la generacion de la DdA (``m03_dda/service._niveles_por_dimension``)
y despues hizo falta en el plan de adecuacion. Aqui vive una vez.

La regla normativa que aplica es la del Anexo I punto 3: una dimension que
ningun tipo de informacion y ningun servicio valora NO se adscribe a ningun
nivel. Se arranca en ``NO_AFECTADA`` y solo sube con valoraciones reales; un
valor que no este en ``NIVELES_CON_ADSCRIPCION`` no cuenta.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m01_categorization.aplicabilidad import (
    DIMENSIONES_ENS,
    NIVELES_CON_ADSCRIPCION,
    NO_AFECTADA,
)

_CONSULTA = sa_text(
    "SELECT valoracion_d, valoracion_i, valoracion_c, valoracion_a, "
    "       valoracion_t "
    "FROM information_types it JOIN systems s ON s.id = it.system_id "
    "WHERE s.project_id = :pid AND it.deleted_at IS NULL "
    "UNION ALL "
    "SELECT valoracion_d, valoracion_i, valoracion_c, valoracion_a, "
    "       valoracion_t "
    "FROM services sv JOIN systems s2 ON s2.id = sv.system_id "
    "WHERE s2.project_id = :pid AND sv.deleted_at IS NULL"
)


async def niveles_por_dimension_del_proyecto(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, str]:
    """``{"D": "MEDIO", ..., "T": "NO_AFECTADA"}`` para el proyecto entero."""
    niveles = dict.fromkeys(DIMENSIONES_ENS, NO_AFECTADA)
    filas = (await db.execute(_CONSULTA, {"pid": str(project_id)})).all()

    for fila in filas:
        for dim, bruto in zip(DIMENSIONES_ENS, fila):
            nivel = str(bruto or "").upper()
            if nivel not in NIVELES_CON_ADSCRIPCION:
                continue
            actual = niveles[dim]
            if actual == NO_AFECTADA or (
                NIVELES_CON_ADSCRIPCION.index(nivel)
                > NIVELES_CON_ADSCRIPCION.index(actual)
            ):
                niveles[dim] = nivel
    return niveles
