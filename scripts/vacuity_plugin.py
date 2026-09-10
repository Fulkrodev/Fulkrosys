"""Plugin de pytest que mide, por test, cuantas filas escribe y cuantas lee.

Sirve al detector de verdad vacua (scripts/vacuity_check.py). La pregunta que
responde no es "¿el test escribio algo?" sino la unica que define la vacuidad:
**¿llego la asercion a examinar alguna fila?**

Un test puede escribir tres filas en una tabla y despues aseverar sobre OTRA que
esta vacia. Escribe mas de cero, asi que un filtro basado solo en escrituras lo
absolveria, y es vacuo igual. Por eso se cuentan las dos cosas por separado:

    filas_escritas         suma de rowcount de INSERT / UPDATE / DELETE
    filas_leidas           suma de rowcount de SELECT
    filas_leidas_reales    igual, pero SIN contar las consultas de solo agregados

La tercera existe porque ``SELECT COUNT(*)`` devuelve SIEMPRE una fila, tambien
sobre una tabla vacia: esa fila contiene el cero. Contarla como lectura hace que
el filtro se deje fuera justo los casos canonicos de vacuidad. Validado: de los
5 tests que se confirmaron vacuos a mano, 4 consultan por COUNT y darian
filas_leidas=1. Con filas_leidas_reales los 5 salen a 0.

La clasificacion de agregados se hace sobre el SQL CAPTURADO EN EJECUCION, no
sobre el fuente del test: se mira la sentencia que el test realmente lanzo.

La medicion es de EJECUCION, no textual: se engancha al evento
``after_cursor_execute`` de SQLAlchemy a nivel de la clase Engine, asi que
capta cualquier sentencia de cualquier conexion que abra el test, incluidas las
de sus fixtures. Verificado con asyncpg: el rowcount de un SELECT llega correcto
(7 filas -> 7, 0 filas -> 0).

Salida: un JSONL con una linea por test, en la ruta que indique
``--vacuity-counters``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

_LECTURA = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_ESCRITURA = re.compile(r"^\s*(INSERT|UPDATE|DELETE|COPY)\b", re.IGNORECASE)
# Proyeccion formada solo por agregados: su cardinalidad es 1 haya datos o no.
_SOLO_AGREGADO = re.compile(
    r"^\s*SELECT\s+(?:count|sum|min|max|avg|bool_and|bool_or|every)\s*\(", re.IGNORECASE)

_actual: dict[str, int] = {"escritas": 0, "leidas": 0, "leidas_reales": 0, "sentencias": 0}
_salida: list[dict] = []


@event.listens_for(Engine, "after_cursor_execute")
def _contar(conn, cursor, statement, parameters, context, executemany):
    rc = getattr(cursor, "rowcount", -1) or 0
    if rc < 0:
        rc = 0
    _actual["sentencias"] += 1
    if _ESCRITURA.match(statement):
        _actual["escritas"] += rc
    elif _LECTURA.match(statement):
        _actual["leidas"] += rc
        if not _SOLO_AGREGADO.match(statement):
            _actual["leidas_reales"] += rc


def pytest_addoption(parser):
    parser.addoption("--vacuity-counters", action="store", default=None,
                     help="ruta del JSONL donde volcar los contadores por test")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _actual.update(escritas=0, leidas=0, leidas_reales=0, sentencias=0)
    yield
    _salida.append({
        "nodeid": item.nodeid,
        "filas_escritas": _actual["escritas"],
        "filas_leidas": _actual["leidas"],
        "filas_leidas_reales": _actual["leidas_reales"],
        "sentencias": _actual["sentencias"],
    })


def pytest_sessionfinish(session, exitstatus):
    destino = session.config.getoption("--vacuity-counters")
    if not destino:
        return
    p = Path(destino)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for reg in _salida:
            fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
