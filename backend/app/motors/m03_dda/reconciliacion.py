"""Plan de reconciliacion del catalogo de medidas: que insertar, que borrar.

POR QUE EXISTE
    `seed_all_fulkro.py` decidia si sembrar con `if existing >= 73: skip`. Un
    contador no sabe que hay dentro. Una base sembrada con el catalogo viejo
    tiene 79 filas -- seis con codigos que NO EXISTEN en el RD 311/2022 -- y
    79 >= 73, asi que el sembrador se saltaba el paso y las seis se quedaban.

    Idempotencia por CONTENIDO: se compara el conjunto de codigos de la base
    contra la fuente verificada (Anexo II contrastado con el PDF del BOE, N0) y
    se dice exactamente que sobra y que falta. Funcion pura: sin BD, sin efectos.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanReconciliacion:
    """Que hay que hacerle a la tabla para que refleje la fuente."""

    insertar: set[str]
    borrar: set[str]

    @property
    def hay_cambios(self) -> bool:
        return bool(self.insertar or self.borrar)

    def explica(self) -> str:
        if not self.hay_cambios:
            return "catalogo al dia: nada que insertar ni que borrar"
        partes = []
        if self.insertar:
            partes.append(f"insertar {len(self.insertar)}: {sorted(self.insertar)}")
        if self.borrar:
            partes.append(
                f"BORRAR {len(self.borrar)} que no existen en el RD 311/2022: "
                f"{sorted(self.borrar)}"
            )
        return " · ".join(partes)


def reconciliar_catalogo(
    codigos_en_bd: set[str],
    codigos_oficiales: set[str],
) -> PlanReconciliacion:
    """Compara lo sembrado contra la fuente verificada.

    Args:
        codigos_en_bd: codigos que hay ahora mismo en `ens_measures`.
        codigos_oficiales: los del Anexo II (73), de la fuente contrastada en N0.

    Returns:
        PlanReconciliacion con lo que falta y lo que sobra.
    """
    return PlanReconciliacion(
        insertar=set(codigos_oficiales) - set(codigos_en_bd),
        borrar=set(codigos_en_bd) - set(codigos_oficiales),
    )
