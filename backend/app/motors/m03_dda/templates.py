"""Plantillas deterministas para justificaciones de no aplicabilidad.

EL DEFECTO QUE ARREGLA
    Hasta el bloque Q habia UNA sola frase, y citaba siempre el eje "categoria":

        "El Anexo II establece que esta medida aplica exclusivamente a sistemas
         de categoria {cat_minima}."

    El dato venia de ``ens_measures.categoria_minima``, una columna
    denormalizada que NO es la que decide la aplicabilidad. Medido sobre el
    proyecto MEDIA del demo: de las 13 exclusiones, 12 son medidas de eje
    "dimension" -- se excluyen porque su dimension no esta afectada o esta en un
    nivel que el Anexo II marca n.a. -- y la frase les atribuia un motivo de
    categoria que es falso. En cuatro de ellas (mp.eq.2, mp.if.6, mp.s.4,
    op.cont.1) ``categoria_minima`` valia MEDIA y el sistema ERA MEDIA, con lo
    que el documento que firma el cliente decia que la medida no aplica porque
    aplica.

    Es el texto que lee el auditor para aceptar una exclusion del Anexo II, asi
    que la frase se deriva ahora del MISMO sitio que decide la exclusion
    (``m01_categorization.aplicabilidad.MotivoNoAplicabilidad``), no de una
    columna paralela.
"""
from __future__ import annotations

from backend.app.motors.m01_categorization.aplicabilidad import (
    MotivoNoAplicabilidad,
)

_CABECERA = (
    "La medida {codigo} ({nombre}) no resulta de aplicación al presente "
    "sistema, clasificado en categoría {system_category} conforme al "
    "Anexo I del RD 311/2022. "
)

# Una frase por subcaso del Anexo II punto 5. Cada una nombra el eje REAL.
_MOTIVO_CATEGORIA = (
    "El Anexo II la exige por la categoría del sistema y marca «n.a.» para la "
    "categoría {system_category}, por lo que queda excluida del alcance."
)
_MOTIVO_SIN_DIMENSIONES = (
    "El Anexo II la exige por el nivel de {dimensiones_nombre}, y "
    "{concordancia_afectada} en este sistema: conforme al Anexo I punto 3, una "
    "dimensión no afectada no se adscribe a ningún nivel y no exige medidas."
)
_MOTIVO_NIVEL_INSUFICIENTE = (
    "El Anexo II la exige por el nivel de {dimensiones_nombre}, y marca «n.a.» "
    "para {detalle_niveles}, por lo que queda excluida del alcance."
)

_NO_CONSTAN = (
    " No se identifican circunstancias que justifiquen su aplicación "
    "voluntaria en este ámbito."
)

_MICRO_SIZES = {"micro", "autonomo", "autónomo", "individual"}

# L-8 (FRENTE L): nota de proporcionalidad para micro/autónomo (CCN-STIC 801).
_PROPORCIONALIDAD_MICRO = (
    " Adicionalmente, conforme al principio de proporcionalidad (CCN-STIC 801 "
    "sec 4.2), el alcance reducido de una organización micro/autónomo refuerza "
    "la no aplicabilidad de esta medida, sin merma de la trazabilidad."
)

_NOMBRE_DIM = {
    "D": "disponibilidad", "I": "integridad", "C": "confidencialidad",
    "A": "autenticidad", "T": "trazabilidad",
}


def _lista(partes: list[str]) -> str:
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def render_no_aplica_justification(
    codigo: str,
    nombre: str,
    system_category: str,
    motivo: MotivoNoAplicabilidad,
    empresa_size: str | None = None,
) -> str:
    """Renderiza la justificación de exclusión a partir del motivo REAL.

    Args:
        codigo, nombre: identifican la medida del Anexo II.
        system_category: categoría del sistema (Anexo I), dato de entrada.
        motivo: el que devuelve
            ``m01_categorization.aplicabilidad.medidas_no_aplicables``. No se
            acepta ``None``: una exclusión sin motivo derivado de la tabla es
            justamente lo que este módulo dejó de emitir.
        empresa_size: L-8, añade la nota de proporcionalidad CCN-STIC 801 4.2.
    """
    if not isinstance(motivo, MotivoNoAplicabilidad):
        raise TypeError(
            "render_no_aplica_justification exige un MotivoNoAplicabilidad "
            "derivado del Anexo II; el texto no se puede escribir sin saber "
            f"por que se excluye la medida (recibido: {type(motivo).__name__})"
        )

    texto = _CABECERA.format(
        codigo=codigo, nombre=nombre, system_category=system_category,
    )

    subcaso = motivo.subcaso
    if subcaso == "categoria_no_exige":
        texto += _MOTIVO_CATEGORIA.format(system_category=system_category)
    else:
        nombres = _lista([
            f"{_NOMBRE_DIM[d]} [{d}]" for d, _n in motivo.dimensiones
        ])
        if subcaso == "sin_dimensiones_afectadas":
            concordancia = (
                "no está afectada" if len(motivo.dimensiones) == 1
                else "ninguna de ellas está afectada"
            )
            texto += _MOTIVO_SIN_DIMENSIONES.format(
                dimensiones_nombre=nombres, concordancia_afectada=concordancia,
            )
        else:
            detalle = _lista([
                (f"el nivel {n} de {_NOMBRE_DIM[d]} [{d}]"
                 if n != "NO_AFECTADA"
                 else f"{_NOMBRE_DIM[d]} [{d}], no afectada")
                for d, n in motivo.dimensiones
            ])
            texto += _MOTIVO_NIVEL_INSUFICIENTE.format(
                dimensiones_nombre=nombres, detalle_niveles=detalle,
            )

    texto += _NO_CONSTAN
    if (empresa_size or "").strip().lower() in _MICRO_SIZES:
        texto += _PROPORCIONALIDAD_MICRO
    return texto
