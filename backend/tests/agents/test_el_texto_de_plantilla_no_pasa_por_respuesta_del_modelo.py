"""Guardia: un resultado de agente SIEMPRE dice de donde salio su texto.

El defecto. Sin ``ANTHROPIC_API_KEY`` la plataforma no falla. ``AgentBase``
devuelve una respuesta de relleno con ``mock=True``; los doce agentes piden
salida estructurada, ese relleno no parsea como JSON, se reintenta tres veces
—tres invocaciones de mentira— y diez de los doce caen a un camino de reserva
de PLANTILLA ESTATICA. El endpoint recibe el resultado, hace ``db.commit()`` y
devuelve 200. Medido:

    $ for f in backend/app/agents/agent_*.py; do \\
        printf "%s %s\\n" "$(basename $f)" "$(grep -c 'fallback' $f)"; done
    agent_04_redactor 9 · agent_06_contratos 16 · agent_11_auditor_virtual 9 ·
    agent_12_coach_cliente 8 · agent_17_cualificador 10 · agent_18_reunion 9 ·
    agent_19_propuestas 11 · agent_20_negociacion 11 · agent_27_clasificador 9 ·
    agent_31_enriquecedor_dda 10

Y la bandera no la miraba nadie: ``grep -rn '"mock"' backend/app`` daba UN solo
consumidor en todo el producto (``m11_copiloto/inline_agents_api.py:298``).

Lo que estos tests exigen: que cada resultado declare ``generado_por``, que
distinga "no hay clave" de "fallo el esquema" —son cosas distintas para quien
decide si el texto vale— y que la ausencia de la marca cuente como NO del
modelo, para que un camino nuevo que se olvide de declararla falle del lado
seguro.

No necesitan base de datos ni clave de API.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.app.agents.procedencia import (
    CLAVE,
    MODELO,
    PLANTILLA_POR_FALLO_DE_ESQUEMA,
    SIN_CLAVE_DE_API,
    VALORES,
    es_del_modelo,
    procedencia,
)


_AGENTES = Path(__file__).resolve().parents[2] / "app/agents"


def _agentes_con_camino_de_reserva() -> list[Path]:
    return sorted(
        p for p in _AGENTES.glob("agent_*.py")
        if "def _build_result" in p.read_text(encoding="utf-8")
    )


def test_hay_diez_agentes_con_camino_de_reserva():
    """Si aparece uno nuevo, este fichero tiene que enterarse."""
    nombres = [p.stem for p in _agentes_con_camino_de_reserva()]
    assert len(nombres) == 10, nombres


@pytest.mark.parametrize(
    "ruta", _agentes_con_camino_de_reserva(), ids=lambda p: p.stem,
)
def test_cada_agente_declara_de_donde_salio_su_texto(ruta):
    """El diccionario de resultado lleva la procedencia, no solo fallback_used.

    ``fallback_used`` existia y no bastaba: decia QUE se habia caido a la
    plantilla, no POR QUE. Sin clave de API tambien se acaba ahi.
    """
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(ruta))
    claves: set[str] = set()
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.FunctionDef) and nodo.name == "_build_result"):
            continue
        for interno in ast.walk(nodo):
            if isinstance(interno, ast.Dict):
                claves.update(
                    k.value for k in interno.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                )
    assert "fallback_used" in claves, f"{ruta.stem} ya no declara fallback_used"
    assert "CLAVE_PROCEDENCIA" in fuente and "procedencia(response" in fuente, (
        f"{ruta.stem} no declara {CLAVE!r} en su resultado: quien lo llame "
        "recibira un 200 con un texto de plantilla indistinguible de una "
        "redaccion del modelo."
    )


def test_sin_clave_de_api_se_distingue_de_un_fallo_de_esquema():
    """Las dos causas acaban en plantilla, y NO son la misma cosa."""
    assert procedencia({"mock": True}, fallback_used=True) == SIN_CLAVE_DE_API
    assert (
        procedencia({"model": "claude-sonnet-4-6"}, fallback_used=True)
        == PLANTILLA_POR_FALLO_DE_ESQUEMA
    )
    assert procedencia({"model": "claude-sonnet-4-6"}, fallback_used=False) == MODELO
    # sin clave manda sobre el fallo de esquema aunque vengan los dos
    assert procedencia({"mock": True}, fallback_used=False) == SIN_CLAVE_DE_API


def test_un_resultado_sin_la_marca_no_cuenta_como_del_modelo():
    """El olvido cae del lado seguro, no del que cuela texto de origen ignoto."""
    assert es_del_modelo({CLAVE: MODELO}) is True
    assert es_del_modelo({}) is False
    assert es_del_modelo(None) is False
    assert es_del_modelo({CLAVE: SIN_CLAVE_DE_API}) is False


def test_el_vocabulario_tiene_exactamente_tres_valores():
    assert set(VALORES) == {MODELO, PLANTILLA_POR_FALLO_DE_ESQUEMA, SIN_CLAVE_DE_API}


def test_la_cadena_de_workflows_arrastra_el_eslabon_mas_debil():
    """El paso N+1 recibe como contexto lo que produjo el N.

    Si un paso salio de una plantilla, lo que venga detras esta construido
    sobre ella: la respuesta final NO puede declararse "del modelo".
    """
    fuente = (
        Path(__file__).resolve().parents[2] / "app/api/v1/workflows_simple.py"
    ).read_text(encoding="utf-8")
    assert "generado_por: str" in fuente, (
        "WorkflowStepResult y WorkflowRunResponse tienen que declarar la "
        "procedencia: este endpoint encadenaba el texto de relleno como "
        "contexto del paso siguiente y lo devolvia como final_response con 200"
    )
    assert "origenes == {MODELO}" in fuente, (
        "la respuesta global solo es del modelo si TODOS los pasos lo son"
    )


def test_la_interfaz_no_canta_exito_cuando_el_texto_no_vino_del_modelo():
    """Los dos sitios que invocan agentes desde la pantalla.

    Los dos hacian ``toast.success`` fijo: un visto bueno verde a algo que no
    habia pasado por ningun modelo. El 200 decia "ha ido bien", y era verdad a
    medias — la llamada fue bien, la redaccion no existio.
    """
    frontend = Path(__file__).resolve().parents[3] / "frontend"
    for relativa in (
        "components/pipeline/LeadDrawer.tsx",
        "components/agents/ActionChip.tsx",
    ):
        fuente = (frontend / relativa).read_text(encoding="utf-8")
        assert "vinoDelModelo(resultado)" in fuente, (
            f"{relativa} da por buena la respuesta sin mirar su procedencia"
        )
        assert "toast.warning" in fuente, (
            f"{relativa} tiene que avisar cuando el texto es de plantilla"
        )
