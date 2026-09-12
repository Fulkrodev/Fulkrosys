"""Ningún test hereda la conexión de otro.

EL FALLO QUE CONGELA
    ``test_bloque_g_metrics_publico_sin_auth`` pasaba en solitario, pasaba con
    todo ``backend/tests/auth``, y fallaba dentro de la batería completa. Ese
    es el perfil exacto de un test que depende del orden, y un test que depende
    del orden no mide lo que dice medir.

    La causa no estaba en el test que se quejaba. El motor de base de datos se
    crea al importar ``backend.app.database`` y guarda conexiones en un pool
    para reutilizarlas. En producción es lo correcto: un proceso, un bucle de
    eventos. Pero ``pytest-asyncio`` abre un bucle NUEVO por test, y una
    conexión de asyncpg queda atada al bucle en el que nació. Cuando el pool se
    la entrega a un test posterior, con otro bucle, la operación revienta con un
    ``RuntimeError``.

    ``/metrics`` es de los pocos endpoints que NO usa la sesión inyectada por el
    arnés: abre la suya con ``async_session()``. Por eso le tocaba la conexión
    heredada. Y como el emisor de métricas captura el error y emite
    ``fulkro_llm_lectura_fallida 1`` en vez de caerse —decisión correcta: una
    métrica que miente es peor que una que falta—, el síntoma visible era
    «faltan métricas del modelo», que no se parece en nada a la causa.

    El mismo mecanismo tumbaba ``test_llm_interactions_pagination`` según con
    quién se ejecutara. Reproducción del par, antes del arreglo:

        pytest backend/tests/api backend/tests/auth
        # 2 failed, 194 passed

    Después: 196 passed.
"""
from __future__ import annotations

import os

import pytest


def test_bajo_la_bateria_el_motor_no_reutiliza_conexiones():
    from backend.app.database import engine

    assert os.environ.get("FULKRO_TESTING") == "1", (
        "este test sólo tiene sentido dentro de la batería (conftest.py fija "
        "FULKRO_TESTING=1)"
    )
    assert type(engine.pool).__name__ == "NullPool", (
        f"el motor usa {type(engine.pool).__name__}: sus conexiones sobreviven "
        "al bucle de eventos que las creó y se las pasan de un test a otro. Ese "
        "es el mecanismo que hacía que un test pasara solo y fallara en la "
        "batería."
    )


@pytest.mark.asyncio
async def test_una_sesion_nueva_funciona_aunque_otra_la_haya_usado_antes(db):
    """El caso de `/metrics`: abrir sesión propia, no la inyectada por el arnés."""
    from sqlalchemy import text

    from backend.app.database import async_session

    for _ in range(2):
        async with async_session() as propia:
            assert await propia.scalar(text("SELECT 1")) == 1
