"""De donde salio el texto: del modelo, o de una plantilla.

El defecto que cierra este modulo. Sin ``ANTHROPIC_API_KEY`` la plataforma no
falla: ``AgentBase`` devuelve una respuesta de relleno marcada ``mock=True``,
los doce agentes piden salida estructurada, ese relleno no parsea como JSON, se
reintenta tres veces —tres invocaciones de mentira— y diez de los doce caen a
un camino de reserva de PLANTILLA ESTATICA con ``fallback_used=True``. El
endpoint recibe ese resultado, hace ``db.commit()`` y devuelve 200.

Nadie miraba la bandera. ``grep -rn '"mock"' backend/app`` encontraba UN solo
consumidor en todo el producto (``m11_copiloto/inline_agents_api.py:298``), y
los endpoints especificos de ``agents/api.py`` ni siquiera la recibian: cada
agente construye su propio diccionario de resultado y ninguno copiaba ``mock``
dentro. Asi que lo que llegaba al llamador era un 200 con un texto de plantilla
indistinguible de uno redactado por el modelo.

Que ``fallback_used`` exista no basta, y por dos razones:

1. No distingue **por que** se cayo a la plantilla. "El esquema fallo tres
   veces" y "no hay clave de API, aqui no se ha llamado a ningun modelo" son
   dos cosas muy distintas para quien tiene que decidir si ese texto vale.
2. Una bandera que nadie mira es documentacion, no control.

De ahi este vocabulario de TRES valores, que viaja en cada resultado de agente
bajo la clave ``generado_por`` y llega hasta la pantalla.
"""
from __future__ import annotations

from typing import Any


#: Lo escribio el modelo. Es el unico valor que vale para un entregable.
MODELO = "modelo"

#: El modelo contesto, pero su salida no cumplio el esquema ni tras los
#: reintentos, y se sirvio una plantilla estatica en su lugar.
PLANTILLA_POR_FALLO_DE_ESQUEMA = "plantilla_por_fallo_de_esquema"

#: No hay ANTHROPIC_API_KEY: no se ha llamado a ningun modelo. El texto es una
#: plantilla, y no hay nada en el que venga de una inferencia.
SIN_CLAVE_DE_API = "sin_clave_de_api"

#: Los tres valores posibles, para validar y para documentar.
VALORES = (MODELO, PLANTILLA_POR_FALLO_DE_ESQUEMA, SIN_CLAVE_DE_API)

#: La clave bajo la que viaja en todo resultado de agente.
CLAVE = "generado_por"


def procedencia(respuesta: dict[str, Any] | None, *, fallback_used: bool) -> str:
    """Deriva la procedencia de la respuesta cruda del agente.

    ``respuesta`` es lo que devolvio ``AgentBase.invoke``, que marca
    ``mock=True`` cuando no hubo llamada real. El orden importa: sin clave de
    API tambien se acaba en la plantilla, y decir solo "fallo el esquema"
    ocultaria la causa de verdad.
    """
    if (respuesta or {}).get("mock"):
        return SIN_CLAVE_DE_API
    return PLANTILLA_POR_FALLO_DE_ESQUEMA if fallback_used else MODELO


def es_del_modelo(resultado: dict[str, Any] | None) -> bool:
    """True solo si el texto lo escribio el modelo.

    Un resultado SIN la clave se considera NO del modelo a proposito: si un
    camino nuevo se olvida de declarar la procedencia, el fallo cae del lado
    seguro en vez de colar texto de origen desconocido como si fuera bueno.
    """
    return (resultado or {}).get(CLAVE) == MODELO


def explicar(valor: str) -> str:
    """Una frase para quien lee la respuesta o la pantalla."""
    return {
        MODELO: "Lo redacto el modelo.",
        PLANTILLA_POR_FALLO_DE_ESQUEMA: (
            "El modelo contesto pero su salida no cumplio el esquema ni tras "
            "los reintentos: esto es una plantilla, revisala antes de usarla."
        ),
        SIN_CLAVE_DE_API: (
            "Sin ANTHROPIC_API_KEY no se ha llamado a ningun modelo: esto es "
            "una plantilla estatica, no una redaccion."
        ),
    }.get(valor, f"procedencia desconocida ({valor!r})")
