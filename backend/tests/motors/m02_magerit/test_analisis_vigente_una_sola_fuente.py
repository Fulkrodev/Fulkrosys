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

EL DESEMPATE, QUE NO ESTABA
    Ninguna de las copias desempataba: ordenaban solo por ``created_at desc``.
    Con ``server_default now()`` todas las filas insertadas en la misma
    transaccion comparten sello (OPS-047), asi que el ganador lo elegia el
    planificador y dos llamadas seguidas podian responder analisis distintos.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]


def test_la_fuente_existe_y_desempata():
    from backend.app.motors.m02_magerit import analisis_vigente as mod

    fuente = Path(mod.__file__).read_text("utf-8")
    assert "created_at.desc()" in fuente
    assert "id.desc()" in fuente, (
        "el desempate por id es justo lo que faltaba: sin el, dos analisis con "
        "el mismo created_at hacen que la respuesta dependa del planificador"
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
