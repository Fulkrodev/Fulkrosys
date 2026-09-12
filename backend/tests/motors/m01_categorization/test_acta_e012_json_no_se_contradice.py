"""El acta E-012 en JSON no puede contradecirse consigo misma.

QUE DEFECTO CONGELA
    El acta E-012 es el documento FIRMABLE que aprueba la categorización. Su
    salida JSON construía la tabla de servicios y tipos de información con

        "D": it.valoracion_d or "BAJO"

    cinco veces, en dos sitios. El bloque ``result`` del MISMO documento sale
    del motor corregido en O2, que sí conoce ``NO_AFECTADA`` (RD 311/2022
    Anexo I punto 3). Resultado: la tabla declaraba BAJO una dimensión que
    nadie valoró y el agregado la daba como no afectada — el documento decía
    dos cosas distintas en la misma página, y la que mentía era la tabla, que
    es la que un auditor lee primero.

    Es el mismo patrón que el ``None`` convertido en BÁSICA: un valor que llega
    a un documento firmable sin venir de la fuente que lo decide.

QUE COMPRUEBA
    1. Una dimensión no afectada sale como tal en la tabla del acta, no como BAJO.
    2. La tabla y el agregado del mismo JSON dicen lo mismo: el agregado es el
       máximo de la tabla, y es NO_AFECTADA cuando nadie la valoró.
    3. Una fila heredada con NULL en la columna tampoco se rellena con BAJO.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup

_DIMS = ("D", "I", "C", "A", "T")
_ORDEN = {"NO_AFECTADA": 0, "BAJO": 1, "MEDIO": 2, "ALTO": 3}


async def _sistema_con_dimension_sin_afectar(async_client, db):
    _, project_id = await setup_test_project(db)
    sr = await async_client.post(
        f"/api/v1/categorization/projects/{project_id}/systems",
        json={"nombre": "Sistema acta E-012", "descripcion": "Q1"},
    )
    system_id = sr.json()["id"]
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/information-types",
        json={"items": [{
            "nombre": "Expedientes",
            "valoracion_d": "MEDIO", "valoracion_i": "MEDIO",
            "valoracion_c": "BAJO",
            # Las dos que nadie valora: se DICEN, no se callan.
            "valoracion_a": "NO_AFECTADA", "valoracion_t": "NO_AFECTADA",
        }]},
    )
    assert r.status_code == 201, r.text
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/services",
        json={"items": [{
            "nombre": "Portal",
            "valoracion_d": "BAJO", "valoracion_i": "BAJO",
            "valoracion_c": "BAJO",
            "valoracion_a": "NO_AFECTADA", "valoracion_t": "NO_AFECTADA",
        }]},
    )
    assert r.status_code == 201, r.text
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/categorize",
        json={"aprobado_por": "Marcos Mata"},
    )
    assert r.status_code in (200, 201), r.text
    return system_id


@pytest.mark.asyncio
async def test_la_tabla_del_acta_no_adscribe_a_bajo_lo_no_afectado(async_client, db):
    system_id = await _sistema_con_dimension_sin_afectar(async_client, db)
    r = await async_client.get(
        f"/api/v1/categorization/systems/{system_id}/acta-e012.json"
    )
    assert r.status_code == 200, r.text
    data = r.json()
    filas = data["information_types"] + data["services"]
    assert filas, "el acta salió sin tabla: este test no está comprobando nada"
    for fila in filas:
        for dim in ("A", "T"):
            assert fila["valoraciones"][dim] == "NO_AFECTADA", (
                f"{fila['nombre']}: la dimensión {dim} no está valorada y el "
                f"acta la declara {fila['valoraciones'][dim]}"
            )


@pytest.mark.asyncio
async def test_la_tabla_y_el_agregado_del_acta_dicen_lo_mismo(async_client, db):
    system_id = await _sistema_con_dimension_sin_afectar(async_client, db)
    data = (await async_client.get(
        f"/api/v1/categorization/systems/{system_id}/acta-e012.json"
    )).json()

    filas = data["information_types"] + data["services"]
    for dim in _DIMS:
        maximo = max(
            (f["valoraciones"][dim] for f in filas),
            key=lambda v: _ORDEN.get(str(v).upper(), 0),
        )
        agregado = data["result"]["dimensiones"][dim]
        assert str(agregado).upper() == str(maximo).upper(), (
            f"el acta se contradice en {dim}: la tabla da {maximo} y el "
            f"resultado agregado da {agregado}"
        )


async def _sistema_todo_bajo(async_client, db):
    """Alta por el camino que existe en CUALQUIER version del contrato.

    A proposito no usa NO_AFECTADA: asi este test tambien corre en el commit
    padre, donde la entrada aun no lo aceptaba, y alli sale en ROJO por el
    motivo que persigue -- el ``or "BAJO"`` del renderizador -- y no por un 422
    del esquema.
    """
    _, project_id = await setup_test_project(db)
    sr = await async_client.post(
        f"/api/v1/categorization/projects/{project_id}/systems",
        json={"nombre": "Sistema acta E-012 nulo", "descripcion": "Q1"},
    )
    system_id = sr.json()["id"]
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/information-types",
        json={"items": [{
            "nombre": "Expedientes", "valoracion_d": "MEDIO",
            "valoracion_i": "MEDIO", "valoracion_c": "BAJO",
            "valoracion_a": "BAJO", "valoracion_t": "BAJO",
        }]},
    )
    assert r.status_code == 201, r.text
    r = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/categorize",
        json={"aprobado_por": "Marcos Mata"},
    )
    assert r.status_code in (200, 201), r.text
    return system_id


@pytest.mark.asyncio
async def test_una_fila_heredada_con_null_tampoco_sale_como_bajo(async_client, db):
    """Datos antiguos: la columna admite NULL y NULL no es BAJO."""
    system_id = await _sistema_todo_bajo(async_client, db)
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE information_types SET valoracion_c = NULL "
                 "WHERE system_id = :sid"),
            {"sid": str(system_id)},
        )
    await db.commit()

    data = (await async_client.get(
        f"/api/v1/categorization/systems/{system_id}/acta-e012.json"
    )).json()
    for fila in data["information_types"]:
        assert fila["valoraciones"]["C"] != "BAJO", (
            "una valoración ausente sale como BAJO en un documento firmable"
        )
        assert fila["valoraciones"]["C"] == "NO_AFECTADA"
