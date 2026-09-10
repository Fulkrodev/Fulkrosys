"""Piezas compartidas por los evaluadores de agentes (BLOQUE D · D2).

Por qué este módulo existe: los tres evaluadores nuevos
(agent_27_clasificador, agent_18_reunion, agent_06_contratos) repiten las
mismas cuatro operaciones —leer un campo extra del `expected_output`,
detectar que el modelo no devolvió JSON, listar claves obligatorias que
faltan y aplicar las frases requeridas/prohibidas—. Tenerlas una sola vez
evita que tres copias se separen.

Restricción de dependencias, que manda sobre el diseño
------------------------------------------------------
El job `evals-arnes` de `.github/workflows/evals.yml` instala **sólo**
`pydantic` y `pyyaml`, y ese job importa el paquete `evaluators` entero.
Por tanto NINGÚN evaluador puede importar `backend.app.agents.*` (arrastra
SQLAlchemy) ni nada del núcleo de la aplicación. Los catálogos y umbrales
que un evaluador necesita se copian en su módulo con un comentario que
apunta al original, y la copia se protege contra deriva desde
`backend/tests/motors/m_observability/test_evaluadores_agentes.py`, que sí
corre con el backend completo instalado y exige igualdad.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from backend.app.motors.m_observability.eval_runner import SALIDA_SIN_JSON
from backend.app.motors.m_observability.golden_datasets_loader import (
    GoldenDatasetEntry,
)


def extra(entry: GoldenDatasetEntry, nombre: str, defecto: Any) -> Any:
    """Lee un campo propio del agente dentro de `expected_output`.

    El esquema `GoldenExpectedOutput` es `extra="allow"`, así que cada
    dataset declara ahí lo suyo (`carpetas_aceptables`,
    `catalogo_obligatorio`, ...). Devolver el `defecto` cuando el campo no
    está es deliberado: **un campo que el dataset no declara NO se
    comprueba**. Así una entrada puede callar sobre, por ejemplo, la acción
    recomendada, en vez de verse obligada a fijar un valor que no tiene
    respuesta correcta.
    """
    extras = entry.expected_output.model_extra or {}
    valor = extras.get(nombre, defecto)
    return defecto if valor is None else valor


def texto_plano(actual: Any) -> str:
    """Serializa la salida real en minúsculas para buscar frases."""
    if actual is None:
        return ""
    if isinstance(actual, str):
        return actual.lower()
    try:
        return json.dumps(actual, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        return str(actual).lower()


def sin_json(actual: Any) -> str | None:
    """Devuelve el motivo si la salida NO es un JSON utilizable.

    Distingue dos cosas que no son la misma:
      - `actual` no es un dict          -> el proveedor devolvió otra cosa.
      - `actual[SALIDA_SIN_JSON]`       -> el modelo SÍ contestó, pero su
        respuesta no se pudo interpretar como JSON. Lo marca el proveedor
        del workflow; ver `SALIDA_SIN_JSON` en eval_runner.

    Ninguno de los dos es un "salto": el modelo tuvo su oportunidad y no
    entregó estructura, así que la entrada cuenta como fallo.
    """
    if not isinstance(actual, dict):
        return f"la salida no es un dict (tipo={type(actual).__name__})"
    if SALIDA_SIN_JSON in actual:
        muestra = str(actual.get(SALIDA_SIN_JSON, ""))[:160]
        return f"el modelo no devolvió JSON interpretable · texto: {muestra!r}"
    return None


def claves_faltantes(actual: dict, obligatorias: Iterable[str]) -> list[str]:
    """Claves obligatorias del esquema del agente que no vienen en la salida."""
    return [clave for clave in obligatorias if clave not in actual]


def frases(entry: GoldenDatasetEntry, actual: Any) -> tuple[list[str], list[str]]:
    """Aplica key_phrases_required / key_phrases_forbidden.

    Se conservan porque son campos canónicos del esquema y los datasets
    nuevos pueden empezar a usarlos sin tocar código. Hoy los tres datasets
    de BLOQUE D los declaran vacíos: la comprobación de estos agentes es
    estructural, y buscar subcadenas dentro de la prosa del modelo sería
    justo el tipo de medida frágil que estos datasets evitan.

    Devuelve (requeridas_ausentes, prohibidas_presentes).
    """
    plano = texto_plano(actual)
    ausentes = [
        f for f in entry.expected_output.key_phrases_required
        if f.lower() not in plano
    ]
    presentes = [
        f for f in entry.expected_output.key_phrases_forbidden
        if f.lower() in plano
    ]
    return ausentes, presentes


def numero(valor: Any) -> float | None:
    """Convierte a float o devuelve None. Los bool NO cuentan como número."""
    if isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def entero(valor: Any) -> int | None:
    """Convierte a int o devuelve None. Los bool NO cuentan como entero."""
    if isinstance(valor, bool):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
