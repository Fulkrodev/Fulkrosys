"""Errores del generador de documentos.

O1 · antes de esto, cuatro generadores rellenaban la categoria del sistema con
"BASICA" cuando no habia ninguna. `categoria_por_regla_del_maximo` devuelve None
A PROPOSITO (RD 311/2022 Anexo I punto 3: sin dimension adscrita no hay
categoria que proyectar), y ese None se convertia en una afirmacion normativa
falsa dentro de un documento FIRMADO: el acta de categorizacion E-012, el
alcance E-155, el informe final E-040 y los documentos rectores.

Rellenar el hueco con la categoria mas baja no es un defecto conservador: es
declarar por debajo, que en el ENS es justo el error que la norma persigue.
"""
from __future__ import annotations


class CategoriaNoDeterminadaError(RuntimeError):
    """No hay categoria para el sistema y el documento la declara.

    Se levanta en vez de rellenar con "BASICA". El mensaje dice que falta y que
    hacer, porque quien lo va a leer es quien tiene que arreglarlo.
    """

    def __init__(self, documento: str, detalle: str | None = None) -> None:
        mensaje = (
            f"No se puede generar {documento}: el sistema no tiene categoria "
            "determinada. Un documento que declara la categoria del sistema no "
            "puede inventarla, y el Anexo I punto 3 del RD 311/2022 no permite "
            "adscribir una dimension no afectada a ningun nivel. "
            "Completa la categorizacion (valora al menos una dimension y "
            "aprueba el acta) y vuelve a generar."
        )
        if detalle:
            mensaje = f"{mensaje} · {detalle}"
        super().__init__(mensaje)
        self.documento = documento
