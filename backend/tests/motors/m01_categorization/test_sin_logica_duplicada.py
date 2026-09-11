"""O1.1 · la regla del maximo del Anexo I vive en UN solo sitio.

EL DEFECTO
    N1 arreglo `service.py`, que arranca las cinco dimensiones en NO_AFECTADA.
    Pero `api.py` conservaba SU PROPIA COPIA de la misma logica:

        level_order = {"BAJO": 1, "MEDIO": 2, "ALTO": 3}          # no conoce NO_AFECTADA
        max_per_dim = {"D": "BAJO", "I": "BAJO", ...}             # arranca en BAJO
        max_level = max(level_order[v] for v in max_per_dim.values())
        projected = {1: "BASICA", 2: "MEDIA", 3: "ALTA"}[max_level]

    Consecuencia medible: un sistema SIN NINGUNA valoracion -- ningun tipo de
    informacion, ningun servicio, o todos sin valorar -- sale por
    `GET /systems/{id}/dimensions` como **BASICA**, con las cinco dimensiones en
    BAJO. El Anexo I punto 3 dice que una dimension no afectada no se adscribe a
    ningun nivel, y sin dimensiones afectadas no hay categoria que proyectar.

    Arreglar una copia y dejar la otra es peor que no arreglar ninguna: el
    sistema se contradice a si mismo segun por donde se le pregunte.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project

BASE = "/api/v1/categorization"
# parents[4] es la raiz del repo. Con parents[3] (= backend/) el rglob de abajo
# miraba en backend/backend/app, que no existe, y el test pasaba en VACIO.
RAIZ = Path(__file__).resolve().parents[4]


async def _sistema(db, project_id: str) -> str:
    sid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:id, :pid, 'Sistema O1', now())"
        ), {"id": str(sid), "pid": project_id})
    await db.flush()
    return str(sid)


# ── el comportamiento ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sistema_sin_valorar_no_sale_como_BASICA(async_client, db):
    """EL CASO: sin una sola dimension afectada no hay categoria que proyectar."""
    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)

    r = await async_client.get(f"{BASE}/systems/{system_id}/dimensions")
    assert r.status_code == 200, r.text
    cuerpo = r.json()

    assert cuerpo["projected_category"] != "BASICA", (
        "un sistema sin ninguna dimension afectada no es BASICA: no hay nada "
        f"que categorizar (Anexo I punto 3) · devolvio {cuerpo}"
    )
    assert cuerpo["projected_category"] is None


@pytest.mark.asyncio
async def test_las_dimensiones_sin_valorar_salen_NO_AFECTADA_no_BAJO(async_client, db):
    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)

    cuerpo = (await async_client.get(f"{BASE}/systems/{system_id}/dimensions")).json()
    for k in ("max_d", "max_i", "max_c", "max_a", "max_t"):
        assert cuerpo[k] == "NO_AFECTADA", (
            f"{k} salio {cuerpo[k]!r}: una dimension que nadie ha valorado no "
            "esta en BAJO, esta sin adscribir"
        )


@pytest.mark.asyncio
async def test_con_una_sola_dimension_afectada_si_proyecta(async_client, db):
    """El arreglo no puede romper el caso normal."""
    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO information_types (id, system_id, nombre, valoracion_c, "
            " created_at) VALUES (:id, :sid, 'Datos', 'ALTO', now())"
        ), {"id": str(uuid.uuid4()), "sid": system_id})
    await db.flush()

    cuerpo = (await async_client.get(f"{BASE}/systems/{system_id}/dimensions")).json()
    assert cuerpo["max_c"] == "ALTO"
    assert cuerpo["projected_category"] == "ALTA"
    assert cuerpo["max_d"] == "NO_AFECTADA"


# ── la duplicacion, cerrada por codigo ────────────────────────────────
def test_no_reaparece_una_segunda_implementacion_de_la_regla_del_maximo():
    """Si alguien vuelve a escribir la tabla de niveles a mano, falla aqui.

    La regla del maximo del Anexo I y el orden de los niveles viven en
    `m01_categorization/service.py` (ImpactLevel.numeric) y se consumen desde
    `aplicabilidad.py`. Cualquier otra copia literal es una divergencia
    esperando a pasar.
    """
    patrones = [
        # {"BAJO": 1, "MEDIO": 2, "ALTO": 3} y variantes de orden de niveles
        re.compile(r'["\']BAJO["\']\s*:\s*1\s*,\s*["\']MEDIO["\']\s*:\s*2'),
        # {1: "BASICA", 2: "MEDIA", 3: "ALTA"} proyeccion de categoria
        re.compile(r'1\s*:\s*["\']BASICA["\']\s*,\s*2\s*:\s*["\']MEDIA["\']'),
        # arranque de las cinco dimensiones en BAJO
        re.compile(r'["\']D["\']\s*:\s*["\']BAJO["\']\s*,\s*["\']I["\']\s*:\s*["\']BAJO["\']'),
    ]
    permitido = {"backend/app/motors/m01_categorization/service.py"}
    # Sin esta guarda el test seria vacuamente verdadero si la ruta estuviera
    # mal: sobre cero ficheros no se comprueba ni una asercion.
    ficheros = list((RAIZ / "backend" / "app").rglob("*.py"))
    assert len(ficheros) > 500, (
        f"solo {len(ficheros)} ficheros barridos: la ruta esta mal y este test "
        "no esta comprobando nada"
    )
    culpables = []
    for py in ficheros:
        rel = str(py.relative_to(RAIZ))
        if rel in permitido:
            continue
        texto = py.read_text("utf-8", errors="ignore")
        for n, linea in enumerate(texto.splitlines(), 1):
            sin_comentario = linea.split("#", 1)[0]
            for pat in patrones:
                if pat.search(sin_comentario):
                    culpables.append(f"{rel}:{n}: {linea.strip()[:90]}")
    assert not culpables, (
        "segunda implementacion de la regla del maximo del Anexo I:\n"
        + "\n".join(culpables)
    )
