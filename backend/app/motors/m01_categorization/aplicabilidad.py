"""Que medidas del Anexo II aplican, y por que. Funcion pura: sin BD, sin efectos.

EL PROBLEMA QUE RESUELVE
    Hasta el bloque N el sistema arrancaba las cinco dimensiones en BAJO
    (`service.py`, `max_per_dim`) y no existia la nocion de "no afectada":
    `grep -i no_afectada backend/app` devolvia cero. Una dimension que nadie
    valoro terminaba en BAJO, y BAJO arrastra medidas que la norma no exige.

    RD 311/2022, Anexo I, punto 3, literal:
        "Cada dimension de seguridad afectada se adscribira a uno de los
         siguientes niveles de seguridad: BAJO, MEDIO o ALTO. Si una dimension
         de seguridad no se ve afectada, NO SE ADSCRIBIRA A NINGUN NIVEL."

    Aqui NO_AFECTADA no contribuye nunca: no aporta medidas y no aparece como
    motivo de ninguna.

COMO DECIDE (Anexo II, punto 5)
    La tercera columna de la tabla dice si la medida se exige por la CATEGORIA
    del sistema o por el NIVEL de una o varias dimensiones. Las tres columnas
    siguientes (BAJO/MEDIO/ALTO, que para las de categoria se leen como
    BASICA/MEDIA/ALTA) dicen si se exige: "n.a." es no exigible, y cualquier
    otra celda ("aplica", "+ R1", "+ [R1 o R2]") es exigible.

    - eje "categoria": aplica si la celda de la categoria del sistema no es n.a.
    - eje "dimension": aplica si ALGUNA de sus dimensiones esta afectada y la
      celda de SU nivel no es n.a. El motivo nombra esa dimension y ese nivel.

La fuente de los dos datos es `m03_dda/anexo2_rd311_2022`, contrastado contra el
PDF del BOE en N0 (diferencial vacio en codigos y aplicabilidad).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.motors.m03_dda.anexo2_rd311_2022 import (
    ANEXO_II_RD311,
    EJE_Y_DIMENSIONES,
)

DIMENSIONES_ENS = ("D", "I", "C", "A", "T")
NIVELES_CON_ADSCRIPCION = ("BAJO", "MEDIO", "ALTO")
NO_AFECTADA = "NO_AFECTADA"
NivelDimension = Literal["NO_AFECTADA", "BAJO", "MEDIO", "ALTO"]

_CATEGORIAS = ("BASICA", "MEDIA", "ALTA")
# Indice de la celda (BAJO/MEDIO/ALTO == BASICA/MEDIA/ALTA) en la tupla del catalogo.
_COLUMNA = {"BAJO": 0, "MEDIO": 1, "ALTO": 2,
            "BASICA": 0, "MEDIA": 1, "ALTA": 2}

_NOMBRE_DIM = {"D": "disponibilidad", "I": "integridad", "C": "confidencialidad",
               "A": "autenticidad", "T": "trazabilidad"}


@dataclass(frozen=True)
class MotivoAplicabilidad:
    """Por que una medida concreta entra en la DdA. Es lo que lee un auditor."""

    eje: Literal["categoria", "dimension"]
    categoria: str | None = None
    dimension: str | None = None
    nivel: str | None = None

    def explica(self) -> str:
        if self.eje == "categoria":
            return f"exigida por la categoria {self.categoria} del sistema"
        return (f"exigida por el nivel {self.nivel} de "
                f"{_NOMBRE_DIM[self.dimension]} [{self.dimension}]")


def _aplica_en_columna(codigo: str, etiqueta: str) -> bool:
    """True si la celda del Anexo II para esa columna NO es n.a."""
    _nombre, *celdas = ANEXO_II_RD311[codigo]
    return bool(celdas[_COLUMNA[etiqueta]])


def valida_niveles(
    niveles: dict[str, str],
    *,
    exigir_alguna_afectada: bool = True,
) -> dict[str, str]:
    """Las cinco dimensiones, decididas explicitamente. Sin valores por defecto.

    Que no haya defecto es el punto: antes el defecto era BAJO y por eso se
    colaba. Aqui, o se decide, o falla.
    """
    faltan = set(DIMENSIONES_ENS) - set(niveles)
    sobran = set(niveles) - set(DIMENSIONES_ENS)
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan dimensiones: {sorted(faltan)}")
        if sobran:
            partes.append(f"dimensiones desconocidas: {sorted(sobran)}")
        raise ValueError(
            "Hay que decidir explicitamente las cinco dimensiones "
            f"(D, I, C, A, T): {'; '.join(partes)}"
        )
    normal = {}
    for dim, valor in niveles.items():
        v = (valor or "").upper()
        if v not in NIVELES_CON_ADSCRIPCION and v != NO_AFECTADA:
            raise ValueError(
                f"Nivel invalido para {dim}: {valor!r}. Validos: "
                f"{list(NIVELES_CON_ADSCRIPCION) + [NO_AFECTADA]}"
            )
        normal[dim] = v
    if exigir_alguna_afectada and all(v == NO_AFECTADA for v in normal.values()):
        raise ValueError(
            "Las cinco dimensiones no afectadas: no hay sistema que categorizar "
            "(RD 311/2022 Anexo I punto 3)."
        )
    return normal


def medidas_aplicables(
    categoria: str,
    niveles_por_dimension: dict[str, str],
    *,
    exigir_alguna_afectada: bool = True,
) -> dict[str, MotivoAplicabilidad]:
    """Medidas del Anexo II que aplican, con el motivo de cada una.

    Args:
        categoria: BASICA | MEDIA | ALTA (categoria del sistema, Anexo I).
        niveles_por_dimension: las CINCO dimensiones D/I/C/A/T, cada una en
            BAJO | MEDIO | ALTO | NO_AFECTADA. No hay valor por defecto.
        exigir_alguna_afectada: si True (defecto), las cinco en NO_AFECTADA es
            un error. Si False, se acepta y la respuesta son SOLO las medidas de
            eje categoria.

            Por que existe el parametro, que no es una valvula de escape: la
            comprobacion "no hay sistema que categorizar" pertenece al acto de
            DERIVAR una categoria, no al de APLICAR la tabla. Cuando la DdA se
            genera, la categoria ya viene de una categorizacion FIRMADA: es un
            dato de entrada, no algo que se este decidiendo aqui. Con la
            categoria dada, "ninguna dimension afectada" tiene respuesta exacta
            en el Anexo II -- las de eje categoria aplican, las de eje dimension
            no -- y negarse a darla seria negarse a leer la tabla.

            El defecto sigue siendo estricto porque atrapa el error comun:
            pasar un diccionario a medio rellenar.

    Returns:
        codigo de medida -> MotivoAplicabilidad. Determinista y ordenado.
    """
    cat = (categoria or "").upper()
    if cat not in _CATEGORIAS:
        raise ValueError(f"Categoria invalida: {categoria!r}. Validas: {list(_CATEGORIAS)}")
    niveles = valida_niveles(
        niveles_por_dimension, exigir_alguna_afectada=exigir_alguna_afectada,
    )

    aplicables: dict[str, MotivoAplicabilidad] = {}
    for codigo in sorted(ANEXO_II_RD311):
        eje, iniciales = EJE_Y_DIMENSIONES[codigo]

        if eje == "categoria":
            if _aplica_en_columna(codigo, cat):
                aplicables[codigo] = MotivoAplicabilidad(eje="categoria", categoria=cat)
            continue

        # Eje dimension: basta con que UNA dimension afectada la exija. Se recorre
        # en orden canonico para que el motivo sea reproducible, y se queda el
        # nivel mas alto que la exige, que es el que manda para los refuerzos.
        mejor: MotivoAplicabilidad | None = None
        mejor_rango = -1
        for inicial in sorted(iniciales):
            nivel = niveles[inicial]
            if nivel == NO_AFECTADA:
                continue  # Anexo I punto 3: no se adscribe a ningun nivel
            if not _aplica_en_columna(codigo, nivel):
                continue
            rango = NIVELES_CON_ADSCRIPCION.index(nivel)
            if rango > mejor_rango:
                mejor_rango = rango
                mejor = MotivoAplicabilidad(eje="dimension", dimension=inicial, nivel=nivel)
        if mejor is not None:
            aplicables[codigo] = mejor

    return aplicables


def diferencia_explicada(
    categoria: str,
    niveles_a: dict[str, str],
    niveles_b: dict[str, str],
) -> list[str]:
    """Medida a medida, que cambia entre dos valoraciones. Para poder ENSENYARLO."""
    a = medidas_aplicables(categoria, niveles_a)
    b = medidas_aplicables(categoria, niveles_b)
    fuera = []
    for codigo in sorted(set(a) - set(b)):
        nombre = ANEXO_II_RD311[codigo][0]
        fuera.append(f"- {codigo} · {nombre} · {a[codigo].explica()}")
    for codigo in sorted(set(b) - set(a)):
        nombre = ANEXO_II_RD311[codigo][0]
        fuera.append(f"+ {codigo} · {nombre} · {b[codigo].explica()}")
    return fuera


def categoria_por_regla_del_maximo(
    niveles_por_dimension: dict[str, str],
) -> str | None:
    """Categoria del sistema por la regla del maximo del Anexo I. UNICA COPIA.

    O1.1 · esta regla estaba escrita TRES veces: aqui (via `compute_category`),
    a mano en `m01_categorization/api.py` y a mano en
    `m06_document_factory/alcance_generator.py`. N1 arreglo una sola, y las otras
    dos siguieron proyectando categoria con las cinco dimensiones arrancando en
    BAJO. Un sistema sin valorar salia BASICA por el endpoint de resumen.

    Arreglar una copia y dejar las otras es peor que no arreglar ninguna: el
    sistema se contradice segun por donde se le pregunte.

    A diferencia de `compute_category`, esta funcion NO exige las cinco
    dimensiones ni aplica el suelo heredado de la AAPP: es la proyeccion simple
    que necesitan los consumidores de solo lectura (resumen de dimensiones,
    generador de alcance).

    Args:
        niveles_por_dimension: dimension -> BAJO | MEDIO | ALTO | NO_AFECTADA.
            Las claves desconocidas y los valores no reconocidos se ignoran.

    Returns:
        "BASICA" | "MEDIA" | "ALTA", o None si NINGUNA dimension esta afectada
        -- que es el caso que el Anexo I punto 3 contempla y las copias a mano
        no: sin dimensiones adscritas no hay categoria que proyectar.
    """
    afectados = [
        NIVELES_CON_ADSCRIPCION.index(v)
        for v in (str(x or "").upper() for x in niveles_por_dimension.values())
        if v in NIVELES_CON_ADSCRIPCION
    ]
    if not afectados:
        return None
    return ("BASICA", "MEDIA", "ALTA")[max(afectados)]
