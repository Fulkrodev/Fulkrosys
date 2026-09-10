"""Identificador de correlacion y registro estructurado por peticion.

EL AGUJERO QUE TAPA
-------------------
Medido el 2026-09-10 (`docs/AUDITORIA_OBSERVABILIDAD.md`): en todo el backend no
habia UN SOLO identificador que permitiera seguir una operacion de punta a punta.
Las apariciones de `request_id` que hay en el codigo son otra cosa —el
identificador de una solicitud de derechos RGPD, o de una peticion de evidencia
al cliente—, no el de una peticion HTTP. Con lo cual, ante «al cliente le fallo
algo a las 18:32», no habia manera de juntar las lineas de registro que
pertenecian a esa peticion y separarlas de las de otras cinco simultaneas.

COMO FUNCIONA
-------------
Un middleware por peticion:
  1. Toma el `X-Request-ID` que venga de fuera (un balanceador o una pasarela
     suelen ponerlo) o genera uno. Se REUTILIZA el de fuera a proposito: si no,
     la traza se parte justo en la frontera del sistema, que es donde mas falta
     hace.
  2. Lo mete en el contexto de loguru, asi que TODA linea de registro emitida
     durante esa peticion lo lleva sin que nadie tenga que acordarse de pasarlo.
  3. Lo devuelve en la cabecera `X-Request-ID` de la respuesta, para que quien
     ve el error en el navegador pueda decir exactamente cual mirar.
  4. Emite UNA linea por peticion con metodo, ruta, codigo y duracion, y de paso
     alimenta las metricas de `metricas.py`.

La ruta que se registra es la PLANTILLA (`/api/v1/projects/{project_id}`), no la
URL concreta. Con la URL concreta, cada UUID crearia una serie nueva en las
metricas y en pocas horas habria decenas de miles: es la forma clasica de
tumbar el sistema de metricas con el propio sistema de metricas.
"""
from __future__ import annotations

import os
import time
import uuid
from contextvars import ContextVar

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.app.motors.m_observability.metricas import (
    HTTP_DURACION,
    HTTP_PETICIONES,
)

CABECERA = "X-Request-ID"

# Disponible para cualquier codigo que quiera anotarlo (por ejemplo, al escribir
# en `llm_interaction_log`), sin arrastrar el objeto `request` por diez capas.
id_peticion: ContextVar[str] = ContextVar("id_peticion", default="-")


def id_actual() -> str:
    """Identificador de la peticion en curso, o `-` si no hay ninguna."""
    return id_peticion.get()


def _limpiar(valor: str) -> str:
    """Un identificador que viene de fuera es entrada del usuario.

    Se recorta y se limita a caracteres inofensivos: si no, cualquiera puede
    inyectar saltos de linea en los registros (partir una linea en dos y
    fabricar una entrada falsa) o meter basura en una cabecera de respuesta.
    """
    limpio = "".join(c for c in valor.strip() if c.isalnum() or c in "-_:.")
    return limpio[:64] or uuid.uuid4().hex


def _plantilla_de_ruta(request) -> str:  # noqa: ANN001
    """La PLANTILLA de la ruta, con los parámetros como huecos.

    No se usa `route.path` directamente: en esta aplicación devuelve la ruta
    RELATIVA al router (medido: `/health` en vez de `/api/v1/health`), y dos
    routers distintos con un `/me` cada uno acabarían en la MISMA serie de
    métricas diciendo cosas distintas.

    Se reconstruye desde la URL real sustituyendo el VALOR de cada parámetro por
    su nombre: `/api/v1/projects/5686.../header` → `/api/v1/projects/{project_id}/header`.
    Así la etiqueta es completa y sigue habiendo una serie por endpoint y no una
    por UUID.

    Si no casó ninguna ruta (un 404), se agrupa todo bajo una etiqueta fija: la
    URL cruda de un 404 la elige quien llama, y sería una vía directa para
    inflar la cardinalidad desde fuera.
    """
    if request.scope.get("route") is None:
        return "<sin-ruta>"
    ruta = request.url.path
    for nombre, valor in (request.scope.get("path_params") or {}).items():
        v = str(valor)
        if v:
            ruta = ruta.replace(v, "{" + nombre + "}")
    return ruta


class MiddlewareCorrelacion(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):  # noqa: ANN001
        entrante = request.headers.get(CABECERA, "")
        rid = _limpiar(entrante) if entrante else uuid.uuid4().hex
        ficha = id_peticion.set(rid)
        t0 = time.perf_counter()
        codigo = 500
        try:
            with logger.contextualize(request_id=rid):
                respuesta = await call_next(request)
                codigo = respuesta.status_code
                respuesta.headers[CABECERA] = rid
                return respuesta
        finally:
            duracion = time.perf_counter() - t0
            # La PLANTILLA de la ruta, no la URL: ver la nota de cabecera sobre
            # cardinalidad. Si Starlette no resolvio ruta (404), se agrupa todo
            # bajo una etiqueta fija por el mismo motivo.
            ruta = _plantilla_de_ruta(request)
            metodo = request.method
            HTTP_PETICIONES.sumar((metodo, ruta, str(codigo)))
            HTTP_DURACION.observar((metodo, ruta), duracion)
            with logger.contextualize(request_id=rid):
                logger.bind(
                    evento="http",
                    metodo=metodo,
                    ruta=ruta,
                    codigo=codigo,
                    duracion_ms=round(duracion * 1000, 2),
                ).info(f"{metodo} {ruta} -> {codigo} ({duracion * 1000:.0f} ms)")
            id_peticion.reset(ficha)


def formato_registro() -> str:
    """Formato de las lineas de registro, con el identificador delante.

    Se deja legible por defecto (una persona mirando `docker logs` es el caso
    normal en este proyecto) y se puede pedir JSON con `FULKRO_LOG_JSON=1` para
    cuando haya un recolector delante. Cambiar el formato por defecto a JSON
    habria hecho ilegible el arranque del demo, que es lo primero que ve
    cualquiera que clona el repositorio.
    """
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[request_id]}</cyan> | "
        "<level>{message}</level>"
    )


def configurar_registro() -> None:
    """Instala el sumidero de registro con el identificador de correlacion.

    Idempotente: `logger.remove()` limpia lo que hubiera antes.
    """
    import sys

    logger.remove()
    if os.environ.get("FULKRO_LOG_JSON") == "1":
        logger.add(sys.stderr, serialize=True, level=os.environ.get("LOG_LEVEL", "INFO"))
    else:
        logger.add(
            sys.stderr,
            format=formato_registro(),
            level=os.environ.get("LOG_LEVEL", "INFO"),
            colorize=True,
        )
    # `extra[request_id]` tiene que existir SIEMPRE o el formato revienta en las
    # lineas emitidas fuera de una peticion (arranque, tareas de fondo).
    logger.configure(extra={"request_id": "-"})
