"""Plantillas deterministas para justificaciones de no aplicabilidad."""

JUSTIFICACION_NO_APLICA_TEMPLATE = (
    "La medida {codigo} ({nombre}) no resulta de aplicación al presente "
    "sistema, clasificado en categoría {system_category} conforme al "
    "Anexo I del RD 311/2022. El Anexo II establece que esta medida "
    "aplica exclusivamente a sistemas de categoría {cat_minima}. No se "
    "identifican circunstancias que justifiquen su aplicación voluntaria "
    "en este ámbito."
)


_MICRO_SIZES = {"micro", "autonomo", "autónomo", "individual"}

# L-8 (FRENTE L): nota de proporcionalidad para micro/autónomo (CCN-STIC 801).
_PROPORCIONALIDAD_MICRO = (
    " Adicionalmente, conforme al principio de proporcionalidad (CCN-STIC 801 "
    "sec 4.2), el alcance reducido de una organización micro/autónomo refuerza "
    "la no aplicabilidad de esta medida, sin merma de la trazabilidad."
)


def render_no_aplica_justification(
    codigo: str,
    nombre: str,
    cat_minima: str,
    system_category: str,
    empresa_size: str | None = None,
) -> str:
    """Renderiza la justificación profesional para una medida no aplicable.

    L-8: si ``empresa_size`` es micro/autónomo, añade la nota de proporcionalidad
    CCN-STIC 801 sec 4.2 (additive · NO altera el determinismo de aplicabilidad ·
    la medida sigue siendo no aplicable por categoría · solo enriquece la
    justificación documental). Sin empresa_size → salida idéntica (backward-compat).
    """
    base = JUSTIFICACION_NO_APLICA_TEMPLATE.format(
        codigo=codigo,
        nombre=nombre,
        cat_minima=cat_minima,
        system_category=system_category,
    )
    if (empresa_size or "").strip().lower() in _MICRO_SIZES:
        base += _PROPORCIONALIDAD_MICRO
    return base
