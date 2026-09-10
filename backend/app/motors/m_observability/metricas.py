"""Metricas en formato de exposicion Prometheus, servidas en `/metrics`.

POR QUE EXISTE ESTE FICHERO
---------------------------
Este motor se llama `m_observability` y, hasta el 2026-09-10, lo que hacia era
otra cosa: registrar llamadas al modelo (`llm_interaction_log`), correr
evaluaciones doradas y anotar eventos de transparencia del Reglamento de IA.
Todo eso es respetable y util, pero no es observabilidad: no habia metricas
expuestas en ningun sitio consumible, no habia trazas y los registros no
llevaban un identificador que permitiera seguir una operacion de punta a punta.
La auditoria esta en `docs/AUDITORIA_OBSERVABILIDAD.md`, con los comandos.

De las dos salidas honestas —renombrar el motor por lo que hace, o anyadir el
minimo real— se eligio la segunda, porque el registro de llamadas al modelo ya
tenia los estados limpios (`success` | `estimado` | `mock` | `error`, catalogo
cerrado por CHECK desde el BLOQUE D) y exponerlos como metricas era casi gratis.

SIN DEPENDENCIAS NUEVAS
-----------------------
El formato de exposicion se escribe a mano. `prometheus_client` no esta en
`backend/requirements.txt` y este repositorio acaba de pasar una campanya sobre
instalabilidad: anyadir una dependencia para generar cuatro lineas de texto
plano seria un mal cambio. El formato es estable y publico, y lo que se emite es
lo que dice la especificacion (`# HELP`, `# TYPE`, y una linea por serie).

DE DONDE SALE CADA NUMERO, QUE ES LO QUE HAY QUE MIRAR AL LEERLO
----------------------------------------------------------------
Hay dos clases de metrica aqui, y NO se comportan igual:

  * Las que se leen de la BASE DE DATOS en cada raspado (las del modelo:
    llamadas por estado, coste acumulado, latencia). Son ciertas para el sistema
    ENTERO y sobreviven a un reinicio. Con dos replicas, las dos dicen lo mismo,
    que es lo correcto: el coste del sistema no se duplica porque haya dos
    procesos.

  * Las que se acumulan EN MEMORIA DEL PROCESO (latencia HTTP y de
    recuperacion). Se pierden al reiniciar y CADA REPLICA TIENE LAS SUYAS. Eso
    no es un defecto, es como funciona este tipo de metrica: quien las agregue
    tiene que sumarlas entre replicas. Se dice aqui porque con dos replicas
    detras de un balanceador es el error de lectura mas facil de cometer.
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Fronteras de los histogramas, en segundos. Elegidas mirando lo que se mide:
# una busqueda hibrida tipica esta en decimas de segundo y una peticion HTTP con
# el modelo detras se va a segundos. Sin fronteras por encima del caso real, el
# p95 no se puede estimar y el histograma solo sirve para contar.
FRONTERAS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)

# Estados del registro de llamadas al modelo. Se emiten SIEMPRE los cuatro,
# aunque valgan cero: una serie que aparece y desaparece segun haya datos rompe
# las alertas de quien la consume (`rate()` sobre una serie ausente no es cero,
# es nada).
ESTADOS_LLM = ("success", "estimado", "mock", "error")


class _Histograma:
    """Histograma acumulativo con candado. Los buckets son `<=` (le, acumulado)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cubos: dict[tuple, list[int]] = defaultdict(
            lambda: [0] * (len(FRONTERAS) + 1)
        )
        self._suma: dict[tuple, float] = defaultdict(float)
        self._cuenta: dict[tuple, int] = defaultdict(int)

    def observar(self, etiquetas: tuple, segundos: float) -> None:
        i = 0
        while i < len(FRONTERAS) and segundos > FRONTERAS[i]:
            i += 1
        with self._lock:
            self._cubos[etiquetas][i] += 1
            self._suma[etiquetas] += segundos
            self._cuenta[etiquetas] += 1

    def series(self) -> list[tuple[tuple, list[int], float, int]]:
        with self._lock:
            return [
                (et, list(self._cubos[et]), self._suma[et], self._cuenta[et])
                for et in list(self._cubos)
            ]


class _Contador:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._v: dict[tuple, float] = defaultdict(float)

    def sumar(self, etiquetas: tuple, cuanto: float = 1.0) -> None:
        with self._lock:
            self._v[etiquetas] += cuanto

    def series(self) -> list[tuple[tuple, float]]:
        with self._lock:
            return list(self._v.items())


# ── registros vivos del proceso ────────────────────────────────────────────
HTTP_PETICIONES = _Contador()          # etiquetas: (metodo, ruta, codigo)
HTTP_DURACION = _Histograma()          # etiquetas: (metodo, ruta)
RECUPERACION_DURACION = _Histograma()  # etiquetas: (rama,)
RECUPERACION_ERRORES = _Contador()     # etiquetas: (rama,)

_ARRANQUE = time.time()


def observar_recuperacion(rama: str, segundos: float) -> None:
    """Anota lo que ha tardado una rama del buscador (lexico · vectorial · fusion)."""
    RECUPERACION_DURACION.observar((rama,), segundos)


def _escapar(v: str) -> str:
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _etiquetas(nombres: tuple[str, ...], valores: tuple) -> str:
    if not nombres:
        return ""
    pares = ",".join(f'{n}="{_escapar(v)}"' for n, v in zip(nombres, valores))
    return "{" + pares + "}"


def _render_histograma(nombre: str, ayuda: str, nombres_et: tuple[str, ...],
                       hist: _Histograma) -> list[str]:
    out = [f"# HELP {nombre} {ayuda}", f"# TYPE {nombre} histogram"]
    for et, cubos, suma, cuenta in hist.series():
        acumulado = 0
        for i, frontera in enumerate(FRONTERAS):
            acumulado += cubos[i]
            base = _etiquetas(nombres_et + ("le",), et + (repr(frontera),))
            out.append(f"{nombre}_bucket{base} {acumulado}")
        acumulado += cubos[-1]
        out.append(f'{nombre}_bucket{_etiquetas(nombres_et + ("le",), et + ("+Inf",))} {acumulado}')
        out.append(f"{nombre}_sum{_etiquetas(nombres_et, et)} {suma}")
        out.append(f"{nombre}_count{_etiquetas(nombres_et, et)} {cuenta}")
    return out


async def _metricas_del_modelo(db: AsyncSession) -> list[str]:
    """Lee el registro de llamadas al modelo. Cierra el circulo del BLOQUE D.

    D1 dejo de contabilizar como exito una llamada que falla, y fijo el catalogo
    de estados con un CHECK. Aqui esos estados se publican: si un dia el sustituto
    del modelo (`mock`) vuelve a colarse en produccion, se ve en una grafica en
    vez de descubrirse leyendo la pantalla de un cliente.
    """
    out: list[str] = []
    try:
        filas = (await db.execute(text(
            "SELECT status, count(*)::bigint, "
            "       coalesce(sum(cost_usd), 0)::float8, "
            "       coalesce(sum(latency_ms), 0)::float8, "
            "       coalesce(sum(total_tokens), 0)::bigint "
            "FROM llm_interaction_log GROUP BY status"
        ))).all()
    except Exception as exc:  # noqa: BLE001
        # Una metrica que miente es peor que una que falta: si la base no
        # responde, se dice que no se pudo leer y no se emiten ceros inventados.
        out.append("# HELP fulkro_llm_lectura_fallida 1 si no se pudo leer el registro de llamadas")
        out.append("# TYPE fulkro_llm_lectura_fallida gauge")
        out.append("fulkro_llm_lectura_fallida 1")
        out.append(f"# error: {_escapar(type(exc).__name__)}")
        return out

    por_estado = {f[0]: f for f in filas}
    out += ["# HELP fulkro_llm_lectura_fallida 1 si no se pudo leer el registro de llamadas",
            "# TYPE fulkro_llm_lectura_fallida gauge",
            "fulkro_llm_lectura_fallida 0"]

    out += ["# HELP fulkro_llm_llamadas_total Llamadas al modelo registradas, por estado",
            "# TYPE fulkro_llm_llamadas_total counter"]
    for estado in ESTADOS_LLM:
        f = por_estado.get(estado)
        out.append(f'fulkro_llm_llamadas_total{{estado="{estado}"}} {f[1] if f else 0}')
    # Un estado fuera del catalogo cerrado no deberia existir (hay un CHECK),
    # pero si apareciera hay que VERLO, no esconderlo tras el bucle de arriba.
    for estado, f in por_estado.items():
        if estado not in ESTADOS_LLM:
            out.append(f'fulkro_llm_llamadas_total{{estado="{_escapar(estado)}"}} {f[1]}')

    out += ["# HELP fulkro_llm_coste_usd_total Coste acumulado de las llamadas al modelo, en dolares",
            "# TYPE fulkro_llm_coste_usd_total counter"]
    for estado in ESTADOS_LLM:
        f = por_estado.get(estado)
        out.append(f'fulkro_llm_coste_usd_total{{estado="{estado}"}} {f[2] if f else 0.0}')

    out += ["# HELP fulkro_llm_latencia_segundos Latencia acumulada de las llamadas al modelo",
            "# TYPE fulkro_llm_latencia_segundos summary"]
    for estado in ESTADOS_LLM:
        f = por_estado.get(estado)
        out.append(f'fulkro_llm_latencia_segundos_sum{{estado="{estado}"}} '
                   f'{(f[3] / 1000.0) if f else 0.0}')
        out.append(f'fulkro_llm_latencia_segundos_count{{estado="{estado}"}} {f[1] if f else 0}')

    out += ["# HELP fulkro_llm_tokens_total Tokens acumulados, por estado",
            "# TYPE fulkro_llm_tokens_total counter"]
    for estado in ESTADOS_LLM:
        f = por_estado.get(estado)
        out.append(f'fulkro_llm_tokens_total{{estado="{estado}"}} {f[4] if f else 0}')
    return out


async def exponer(db: AsyncSession) -> str:
    """Devuelve el cuerpo completo de `/metrics`."""
    lineas: list[str] = []

    lineas += ["# HELP fulkro_proceso_segundos_en_pie Segundos desde que arranco ESTE proceso",
               "# TYPE fulkro_proceso_segundos_en_pie gauge",
               f"fulkro_proceso_segundos_en_pie {time.time() - _ARRANQUE:.3f}"]

    lineas += ["# HELP fulkro_http_peticiones_total Peticiones HTTP servidas por ESTE proceso",
               "# TYPE fulkro_http_peticiones_total counter"]
    for et, v in HTTP_PETICIONES.series():
        lineas.append(f"fulkro_http_peticiones_total{_etiquetas(('metodo', 'ruta', 'codigo'), et)} {int(v)}")

    lineas += _render_histograma(
        "fulkro_http_duracion_segundos",
        "Duracion de las peticiones HTTP en ESTE proceso",
        ("metodo", "ruta"), HTTP_DURACION)

    lineas += _render_histograma(
        "fulkro_recuperacion_duracion_segundos",
        "Duracion de cada rama del buscador del corpus en ESTE proceso",
        ("rama",), RECUPERACION_DURACION)

    lineas += ["# HELP fulkro_recuperacion_errores_total Busquedas que fallaron, por rama",
               "# TYPE fulkro_recuperacion_errores_total counter"]
    for et, v in RECUPERACION_ERRORES.series():
        lineas.append(f"fulkro_recuperacion_errores_total{_etiquetas(('rama',), et)} {int(v)}")

    lineas += await _metricas_del_modelo(db)
    return "\n".join(lineas) + "\n"


def token_esperado() -> str | None:
    """Token de raspado. Sin el, `/metrics` no se sirve fuera de desarrollo."""
    return os.environ.get("FULKRO_METRICS_TOKEN") or None


def es_produccion() -> bool:
    return os.environ.get("APP_ENV", "development").lower() in ("production", "prod")
