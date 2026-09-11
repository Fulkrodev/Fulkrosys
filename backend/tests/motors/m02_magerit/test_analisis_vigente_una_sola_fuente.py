"""O2 · "cual es el analisis MAGERIT del proyecto" se contesta en un solo sitio.

EL DEFECTO
    La misma pregunta estaba respondida OCHO veces:

        m22_discovery/paso6_asset_discoverer._get_or_create_magerit_analysis
        m02_magerit/portal_api._get_active_analysis_id
        m02_magerit/portal_api.magerit_summary        (copia en linea)
        m02_magerit/threat_auto_mapper._resolve_analysis
        m08_verification/scope_deriver                (crown jewels)
        dev/router.py x2                              (sembrado de demo)
        core/workflow_gates.require_magerit_analysis  (un COUNT, no un SELECT)

    Cuatro salieron leyendo el codigo; las otras cuatro las encontro el propio
    guard de mas abajo al correrlo por primera vez. Y el panel de administracion
    no la hacia en absoluto: guardaba el id en estado de React. Ocho copias mas
    una ausencia es el mismo patron que ya aparecio en la regla del maximo y en
    el bienio del art. 31 -- se arregla una copia y las otras se quedan atras.

EL ORDEN, QUE ERA EL PROBLEMA
    Ninguna de las copias desempataba: ordenaban solo por ``created_at desc``.
    Y ``created_at`` lleva ``server_default now()``, que en PostgreSQL devuelve
    el sello de INICIO DE TRANSACCION: dos analisis creados en la misma
    transaccion comparten ``created_at`` al microsegundo y el ganador lo elige
    el planificador. De ese analisis cuelga el informe E-028, que se firma.

    Un resolutor unico lo arregla hoy; el noveno llamante que escriba la
    consulta a mano lo vuelve a romper. Por eso la garantia esta en la BASE
    (columna ``es_vigente`` + indice unico parcial + dos disparadores,
    migracion ``magerit_analisis_vigente_001``) y aqui ya no hay nada que
    ordenar.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[4]


def test_la_fuente_existe_y_no_ordena():
    from backend.app.motors.m02_magerit import analisis_vigente as mod

    fuente = Path(mod.__file__).read_text("utf-8")
    assert "es_vigente" in fuente
    assert "order_by" not in fuente, (
        "ordenar era el defecto: el vigente es un hecho marcado en la fila, "
        "no el resultado de un ORDER BY que puede empatar"
    )
    assert callable(mod.analisis_vigente)
    assert callable(mod.id_analisis_vigente)


def test_nadie_mas_reimplementa_la_consulta():
    """Ningun otro fichero vuelve a escribir el SELECT de "ultimo analisis".

    La huella es inconfundible: filtrar ``MageritAnalysis.project_id`` y
    ordenar por ``created_at`` en la misma consulta.
    """
    ficheros = [
        p for p in (RAIZ / "backend" / "app").rglob("*.py")
        if p.name != "analisis_vigente.py"
    ]
    assert len(ficheros) > 500, f"solo {len(ficheros)} ficheros barridos"

    malos = []
    for py in ficheros:
        texto = py.read_text("utf-8", errors="ignore")
        if "MageritAnalysis" not in texto:
            continue
        # Se mira por bloques de consulta, no linea a linea: el SELECT esta
        # partido en varias lineas encadenadas.
        for m in re.finditer(
            r"select\(\s*MageritAnalysis\s*\)(?:[^;]{0,400}?)"
            r"MageritAnalysis\.created_at",
            texto,
            re.S,
        ):
            linea = texto[: m.start()].count("\n") + 1
            malos.append(f"{py.relative_to(RAIZ)}:{linea}")

    assert not malos, (
        "vuelve a haber copias de la consulta del analisis vigente; usa "
        "m02_magerit.analisis_vigente:\n  " + "\n  ".join(malos)
    )


def test_los_llamantes_la_usan():
    """Los sitios que tenian copia ahora llaman a la fuente."""
    esperado = {
        "backend/app/motors/m22_discovery/paso6_asset_discoverer.py",
        "backend/app/motors/m02_magerit/portal_api.py",
        "backend/app/motors/m02_magerit/threat_auto_mapper.py",
        "backend/app/motors/m08_verification/scope_deriver.py",
        "backend/app/dev/router.py",
        "backend/app/core/workflow_gates.py",
        "backend/app/motors/m02_magerit/api.py",
    }
    for rel in sorted(esperado):
        texto = (RAIZ / rel).read_text("utf-8")
        assert "analisis_vigente" in texto, (
            f"{rel} ya no llama a la fuente unica del analisis vigente"
        )


# ================================================================
# La garantia esta en la base, no en que los llamantes se porten bien
# ================================================================


@pytest.mark.asyncio
async def test_la_base_impide_dos_vigentes_en_el_mismo_proyecto(db):
    """El indice unico parcial es la garantia que no se puede esquivar."""
    from sqlalchemy import text as sa_text

    fila = (await db.execute(sa_text(
        "SELECT indexdef FROM pg_indexes "
        "WHERE indexname = 'uq_magerit_analysis_vigente_por_proyecto'"
    ))).scalar()
    assert fila, "falta el indice unico parcial del analisis vigente"
    assert "UNIQUE" in fila
    assert "es_vigente" in fila


@pytest.mark.asyncio
async def test_dos_analisis_en_la_misma_transaccion_dejan_uno_vigente(db):
    """La reproduccion exacta del defecto.

    Dos filas insertadas en la MISMA transaccion comparten ``created_at`` al
    microsegundo -- ``now()`` devuelve el sello de inicio de transaccion --, asi
    que la consulta vieja (``ORDER BY created_at DESC``) empataba y el ganador
    lo elegia el planificador. Aqui se comprueba que ya no hay empate posible.
    """
    from sqlalchemy import text as sa_text

    from backend.app.motors.m02_magerit.analisis_vigente import analisis_vigente
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)

    ids = []
    for nombre in ("primero", "segundo"):
        r = await db.execute(sa_text(
            "INSERT INTO magerit_analysis (id, project_id, name, version, "
            "  status, calculation_mode, methodology_version) "
            "VALUES (gen_random_uuid(), :pid, :n, 1, 'draft', 'qualitative', "
            "  'MAGERIT v3') RETURNING id, created_at"
        ), {"pid": str(project_id), "n": nombre})
        ids.append(r.first())
    await db.flush()

    assert ids[0][1] == ids[1][1], (
        "el escenario deja de reproducir el defecto si los sellos difieren"
    )

    vigentes = (await db.execute(sa_text(
        "SELECT count(*) FROM magerit_analysis "
        "WHERE project_id = :pid AND es_vigente AND deleted_at IS NULL"
    ), {"pid": str(project_id)})).scalar()
    assert vigentes == 1, f"{vigentes} analisis vigentes en el mismo proyecto"

    elegido = await analisis_vigente(db, project_id)
    assert elegido is not None
    assert elegido.id == ids[1][0], "el vigente es el ultimo insertado"


@pytest.mark.asyncio
async def test_borrar_el_vigente_asciende_al_siguiente(db):
    """Borrar el vigente no puede dejar al proyecto sin analisis vigente."""
    from sqlalchemy import text as sa_text

    from backend.app.motors.m02_magerit.analisis_vigente import analisis_vigente
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    ids = []
    for nombre in ("viejo", "nuevo"):
        r = await db.execute(sa_text(
            "INSERT INTO magerit_analysis (id, project_id, name, version, "
            "  status, calculation_mode, methodology_version) "
            "VALUES (gen_random_uuid(), :pid, :n, 1, 'draft', 'qualitative', "
            "  'MAGERIT v3') RETURNING id"
        ), {"pid": str(project_id), "n": nombre})
        ids.append(r.scalar())
    await db.flush()

    await db.execute(sa_text(
        "UPDATE magerit_analysis SET deleted_at = now() WHERE id = :aid"
    ), {"aid": str(ids[1])})
    await db.flush()

    quedan = await analisis_vigente(db, project_id)
    assert quedan is not None, "el proyecto se quedo sin analisis vigente"
    assert quedan.id == ids[0]
