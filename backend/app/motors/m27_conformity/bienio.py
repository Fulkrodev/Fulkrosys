"""El plazo de dos anyos del art. 31 del RD 311/2022, en un solo sitio.

LA CITA, del PDF del BOE verificado en N0
    Articulo 31.1: "Los sistemas de informacion comprendidos en el ambito de
    aplicacion de este real decreto seran objeto de una auditoria regular
    ordinaria, AL MENOS CADA DOS ANYOS, que verifique el cumplimiento de los
    requerimientos del ENS."

    Y el mismo articulo: "El plazo de dos anyos senyalado en los parrafos
    anteriores podra extenderse durante tres meses cuando concurran impedimentos
    de fuerza mayor no imputables a la entidad titular".

POR QUE ESTE MODULO
    El plazo estaba escrito CINCO veces y ya habia divergido: 24 meses x 30 dias
    = 720 en un sitio, 730 en otros tres. La fecha de caducidad de la ruta de
    conformidad iba diez dias por delante de la del planificador de renovacion.

    Y ninguna de las dos era correcta. La norma dice ANYOS, no dias: 730 = 2x365
    se come el dia bisiesto y adelanta la caducidad un dia sobre cualquier fecha
    anterior al 29 de febrero de un anyo bisiesto. En un plazo regulatorio que
    se graba en un entregable firmado, eso es una fecha incorrecta.
"""
from __future__ import annotations

from datetime import date

# Art. 31.1 RD 311/2022. Es un periodo en ANYOS porque la norma lo dice en anyos.
PERIODO_AUDITORIA_ANYOS = 2

# Art. 31.1, ultimo parrafo: prorroga por fuerza mayor. NO se aplica sola.
PRORROGA_FUERZA_MAYOR_MESES = 3


def proxima_fecha_bienal(desde: date, anyos: int = PERIODO_AUDITORIA_ANYOS) -> date:
    """Suma anyos de CALENDARIO, no multiplos de 365 dias.

    El 29 de febrero no existe en un anyo no bisiesto: se ajusta al 28, que es
    el criterio habitual para plazos legales y el unico que no inventa una fecha.
    """
    try:
        return desde.replace(year=desde.year + anyos)
    except ValueError:
        # 29 de febrero -> 28 de febrero del anyo destino.
        return desde.replace(year=desde.year + anyos, day=28)
