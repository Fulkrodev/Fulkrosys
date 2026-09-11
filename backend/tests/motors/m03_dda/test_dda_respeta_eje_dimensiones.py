"""O1 · la DdA que se firma respeta el eje "dimension" del Anexo II.

EL HALLAZGO, que es el peor de todo el bloque O
    `m01_categorization/aplicabilidad.medidas_aplicables` -- la funcion pura que
    el bloque N escribio, probo con un test dorado y documento en ADR-061 --
    tenia **CERO llamadores en produccion**:

        $ grep -rn "medidas_aplicables" backend/app --include=*.py \\
            | grep -v aplicabilidad.py
        (vacio)

    La DdA real la generaba `DdaService._measure_applies`, que solo mira la
    categoria:

        if category == CategoriaSistema.BASICA:
            return measure.aplica_basica
        ...

    O sea: N arreglo el calculo y lo enchufo a la PANTALLA (portal_api muestra
    el eje y el nivel exigido), pero no a la GENERACION. El documento que el
    cliente firma seguia saliendo del camino viejo. Es el mismo patron que
    O1.1 -- arreglar una copia y dejar la otra -- un nivel mas arriba.

QUE CAMBIA
    El Anexo II punto 5 dice que una medida se exige por la CATEGORIA del
    sistema o por el NIVEL de una o varias dimensiones. Una DdA que solo mira la
    categoria mete medidas que cuelgan de dimensiones NO AFECTADAS, y no puede
    justificar por que aplica cada una -- que es justo lo que un auditor pide.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project

BASE = "/api/v1/dda"


async def _proyecto_categorizado(db, valoraciones: dict[str, str | None]):
    """Proyecto con sistema, tipo de informacion valorado y categorizacion firmada."""
    _, project_id = await setup_test_project(db)
    system_id, it_id, cat_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:id, :pid, 'Sistema DdA', now())"
        ), {"id": str(system_id), "pid": project_id})
        await db.execute(text(
            "INSERT INTO information_types (id, system_id, nombre, valoracion_d, "
            " valoracion_i, valoracion_c, valoracion_a, valoracion_t, created_at) "
            "VALUES (:id, :sid, 'Datos', :d, :i, :c, :a, :t, now())"
        ), {"id": str(it_id), "sid": str(system_id), **{
            k.lower(): valoraciones.get(k) for k in ("D", "I", "C", "A", "T")}})
        await db.execute(text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, "
            " fecha_acta, version, aprobado_por, created_at) "
            "VALUES (:id, :sid, 'MEDIA', :f, 1, 'RSEG Test', now())"
        ), {"id": str(cat_id), "sid": str(system_id), "f": date.today()})
    await db.flush()
    return project_id


async def _codigos_que_aplican(db, project_id: str) -> set[str]:
    filas = (await db.execute(text(
        "SELECT m.codigo FROM dda_entries e "
        "JOIN ens_measures m ON m.id = e.measure_id "
        "WHERE e.project_id = :p AND e.aplicabilidad != 'no_aplica' "
        "  AND e.deleted_at IS NULL"
    ), {"p": project_id})).all()
    return {f[0] for f in filas}


@pytest.mark.asyncio
async def test_una_dimension_no_afectada_no_arrastra_su_medida_a_la_dda(
    async_client, db,
):
    """EL CASO: op.exp.8 se exige por TRAZABILIDAD. Sin trazabilidad, fuera."""
    # Trazabilidad SIN valorar (None) = NO AFECTADA (Anexo I punto 3).
    pid_sin_t = await _proyecto_categorizado(
        db, {"D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "MEDIO", "T": None},
    )
    r = await async_client.post(
        f"{BASE}/generate",
        json={"project_id": pid_sin_t, "system_category": "MEDIA",
              "responsable": "RSEG Test"},
    )
    assert r.status_code == 201, r.text
    aplican = await _codigos_que_aplican(db, pid_sin_t)

    assert "op.exp.8" not in aplican, (
        "op.exp.8 (Registro de la actividad) se exige por el nivel de "
        "TRAZABILIDAD. Con la trazabilidad no afectada no puede aplicar: la DdA "
        "esta ignorando el eje de dimensiones del Anexo II."
    )


@pytest.mark.asyncio
async def test_con_la_dimension_afectada_la_medida_si_entra(async_client, db):
    """El arreglo no puede dejar fuera lo que si se exige."""
    pid = await _proyecto_categorizado(
        db, {"D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "MEDIO", "T": "MEDIO"},
    )
    r = await async_client.post(
        f"{BASE}/generate",
        json={"project_id": pid, "system_category": "MEDIA",
              "responsable": "RSEG Test"},
    )
    assert r.status_code == 201, r.text
    aplican = await _codigos_que_aplican(db, pid)
    assert "op.exp.8" in aplican


@pytest.mark.asyncio
async def test_las_de_categoria_no_dependen_de_ninguna_dimension(async_client, db):
    """org.1 se exige POR CATEGORIA: entra aunque no haya dimensiones afectadas."""
    pid = await _proyecto_categorizado(
        db, {"D": None, "I": None, "C": "MEDIO", "A": None, "T": None},
    )
    r = await async_client.post(
        f"{BASE}/generate",
        json={"project_id": pid, "system_category": "MEDIA",
              "responsable": "RSEG Test"},
    )
    assert r.status_code == 201, r.text
    aplican = await _codigos_que_aplican(db, pid)
    for codigo in ("org.1", "org.2", "org.3", "org.4"):
        assert codigo in aplican, f"{codigo} se exige por categoria y falta"
    # op.cont.1 se exige por DISPONIBILIDAD, que aqui no esta afectada.
    assert "op.cont.1" not in aplican


@pytest.mark.asyncio
async def test_la_funcion_pura_tiene_llamadores_en_produccion(db):
    """Si vuelve a quedarse sin enchufar, falla aqui y no dentro de un anyo."""
    import re
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[4]
    llamadores = []
    for py in (raiz / "backend" / "app").rglob("*.py"):
        if py.name == "aplicabilidad.py":
            continue
        for i, linea in enumerate(py.read_text("utf-8", errors="ignore").splitlines(), 1):
            if re.search(r"\bmedidas_aplicables\s*\(", linea.split("#", 1)[0]):
                llamadores.append(f"{py.relative_to(raiz)}:{i}")
    assert llamadores, (
        "`medidas_aplicables` no la llama nadie en produccion: la DdA se estaria "
        "generando otra vez por el camino que ignora el eje de dimensiones"
    )
