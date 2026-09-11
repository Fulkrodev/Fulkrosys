"""Detecta y marca categorizaciones calculadas con la regla del Anexo I incorrecta.

Regla 2 del bloque O · ADR-061 reconocia que las categorizaciones ya guardadas
conservan sus cinco dimensiones en BAJO y nadie las habia revisado. Eso es un
hueco funcional, no una decision con contrapartida: de la categoria del sistema
cuelga que medidas aplican, la DdA, el plan y el alcance.

QUE HACE ESTE MODULO
    Recomputa cada categorizacion desde su `input_snapshot` con la regla
    correcta -- las dimensiones no valoradas NO se adscriben a ningun nivel
    (Anexo I punto 3) -- y compara con la categoria guardada.

QUE NO HACE, DELIBERADAMENTE
    No sobrescribe ninguna categoria. Una categorizacion es un acto aprobado y
    firmado; cambiarla por detras seria falsificar un acta. Marca, y que la
    persona responsable rehaga el acto.
"""
from __future__ import annotations

import logging

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m01_categorization.aplicabilidad import (
    DIMENSIONES_ENS,
    NIVELES_CON_ADSCRIPCION,
    NO_AFECTADA,
    categoria_por_regla_del_maximo,
)

logger = logging.getLogger(__name__)

MOTIVO_SIN_SNAPSHOT = (
    "No hay input_snapshot con el que verificar el calculo. La categorizacion "
    "es anterior al arreglo del eje de dimensiones (RD 311/2022 Anexo I punto "
    "3) y no se puede comprobar si le afecta: hay que rehacerla."
)
MOTIVO_DIFIERE = (
    "Calculada con la regla anterior, que adscribia a BAJO las dimensiones NO "
    "AFECTADAS. Recomputada segun el Anexo I punto 3 da {nueva} en vez de "
    "{vieja}: hay que rehacer la categorizacion."
)


def niveles_desde_snapshot(snapshot: dict | None) -> dict[str, str] | None:
    """Máximo por dimension a partir del snapshot, sin adscribir lo no valorado.

    Returns None si el snapshot no tiene la forma esperada: no se adivina.
    """
    if not isinstance(snapshot, dict):
        return None
    items = []
    for clave in ("information_types", "services"):
        valor = snapshot.get(clave)
        if isinstance(valor, list):
            items.extend(valor)
    if not items and not any(k in snapshot for k in ("information_types", "services")):
        return None

    niveles = dict.fromkeys(DIMENSIONES_ENS, NO_AFECTADA)
    for item in items:
        vals = (item or {}).get("valoraciones")
        if not isinstance(vals, dict):
            continue
        for dim in DIMENSIONES_ENS:
            bruto = vals.get(dim)
            nivel = str(bruto or "").upper()
            if nivel not in NIVELES_CON_ADSCRIPCION:
                continue  # Anexo I punto 3: sin valorar = sin adscribir
            actual = niveles[dim]
            if actual == NO_AFECTADA or (
                NIVELES_CON_ADSCRIPCION.index(nivel)
                > NIVELES_CON_ADSCRIPCION.index(actual)
            ):
                niveles[dim] = nivel
    return niveles


async def marcar_categorizaciones_afectadas(db: AsyncSession) -> int:
    """Marca las categorizaciones que la regla correcta habria dejado distintas.

    Idempotente: solo mira las que aun no estan marcadas, asi que una segunda
    pasada devuelve 0.

    Returns:
        Cuantas filas se han marcado en ESTA pasada.
    """
    filas = (await db.execute(sa_text(
        "SELECT id, categoria_resultante, input_snapshot FROM categorizations "
        "WHERE requiere_recategorizacion IS NOT TRUE AND deleted_at IS NULL"
    ))).all()

    marcadas = 0
    for cat_id, categoria, snapshot in filas:
        niveles = niveles_desde_snapshot(snapshot)
        if niveles is None:
            motivo = MOTIVO_SIN_SNAPSHOT
        else:
            nueva = categoria_por_regla_del_maximo(niveles)
            if nueva == (categoria or "").upper():
                continue  # sigue siendo correcta: no se toca
            motivo = MOTIVO_DIFIERE.format(
                nueva=nueva if nueva is not None else "SIN CATEGORIZAR",
                vieja=categoria,
            )
        await db.execute(sa_text(
            "UPDATE categorizations SET requiere_recategorizacion = TRUE, "
            " motivo_recategorizacion = :m WHERE id = :id"
        ), {"m": motivo, "id": str(cat_id)})
        marcadas += 1

    if marcadas:
        logger.warning(
            "Marcadas %s categorizaciones que exigen rehacerse (Anexo I punto 3)",
            marcadas,
        )
    return marcadas
