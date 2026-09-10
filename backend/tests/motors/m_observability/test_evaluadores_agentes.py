"""Evaluadores de agentes de BLOQUE D · D2: deriva, auto-consistencia y fallo.

Qué se demuestra aquí, y con qué comando
----------------------------------------
    docker run --rm -v "$PWD:/app" -w /app -e PYTHONPATH=/app \
      fulkro/backend:test \
      python -m pytest backend/tests/motors/m_observability/test_evaluadores_agentes.py -v

Ninguno de estos tests necesita base de datos ni clave de API: corren en el
job `test` de CI, que va con `-m "not requires_db"`.

Los tres grupos, por orden de importancia:

1. **Deriva de catálogos.** Los evaluadores copian a mano los enumerados y
   umbrales de sus agentes, porque el job `evals-arnes` importa el paquete
   `evaluators` con sólo pydantic y pyyaml instalados y los módulos de los
   agentes arrastran SQLAlchemy. Estos tests SÍ importan los dos lados y
   exigen igualdad: si alguien toca un catálogo del agente y no la copia,
   salta aquí, no en producción.

2. **Auto-consistencia.** La misma comprobación que hace el gate del arnés,
   repetida en pytest para que un fallo se vea también en la suite local.

3. **El evaluador puede decir que no.** Un evaluador que sólo sabe aprobar
   no es un evaluador. Por cada agente hay al menos un caso mutado que TIENE
   que fallar, con el motivo concreto.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

# Importar el paquete registra evaluadores y constructores sintéticos.
from backend.app.motors.m_observability import evaluators  # noqa: F401
from backend.app.motors.m_observability.eval_runner import (
    _AGENT_EVALUATORS,
    _AGENT_SYNTHETIC_OUTPUTS,
    SALIDA_SIN_JSON,
    build_synthetic_output,
    get_synthetic_output_builder,
)
from backend.app.motors.m_observability.evaluators import (
    agent_06_contratos_evaluator as ev06,
    agent_18_reunion_evaluator as ev18,
    agent_27_clasificador_evaluator as ev27,
)
from backend.app.motors.m_observability.golden_datasets_loader import (
    list_available_datasets,
    load_golden_dataset,
)


pytestmark = pytest.mark.golden

AGENTES_D2 = ("agent_27_clasificador", "agent_18_reunion", "agent_06_contratos")


# ═══════════════════════════════════════════════════════════════════════════
# 1 · Deriva entre la copia del evaluador y el original del agente
# ═══════════════════════════════════════════════════════════════════════════


def test_a27_catalogo_de_carpetas_no_ha_derivado():
    from backend.app.agents import agent_27_clasificador as a27

    assert ev27._NOMBRES_CARPETA == a27.FOLDER_NAMES
    assert set(ev27._NOMBRES_CARPETA) == set(a27.VALID_FOLDER_CODES)
    assert ev27._UMBRAL_AUTO_APROBABLE == a27._AUTO_APPROVABLE_THRESHOLD
    assert ev27._UMBRAL_ALTERNATIVA_RELEVANTE == a27._ALT_REVIEW_THRESHOLD
    assert ev27._TIPOS_TAG == a27._VALID_TAG_TYPES
    assert ev27._CLAVES_OBLIGATORIAS == a27._REQUIRED_KEYS


def test_a18_enumerados_no_han_derivado():
    from backend.app.agents import agent_18_reunion as a18

    assert ev18._CATEGORIAS == a18._CATEGORIAS
    assert ev18._MADUREZ == a18._MADUREZ
    assert ev18._VIABILIDAD == a18._VIABILIDAD
    assert ev18._IMPACTO == a18._IMPACTO
    assert ev18._ESFUERZO == a18._ESFUERZO
    assert ev18._CLAVES_OBLIGATORIAS == a18._REQUIRED_KEYS


def test_a06_enumerados_no_han_derivado():
    from backend.app.agents import agent_06_contratos as a06

    assert ev06._NIVELES == a06._COMPLIANCE_LEVELS
    assert ev06._CALIDADES == a06._CLAUSE_QUALITY
    assert ev06._SEVERIDADES == a06._SEVERITIES
    assert ev06._ACCIONES == a06._ACTIONS
    assert ev06._URGENCIAS == a06._URGENCIES
    assert ev06._CLAVES_OBLIGATORIAS == a06._REQUIRED_KEYS


def test_a06_catalogo_declarado_en_el_dataset_coincide_con_el_del_agente():
    """El `catalogo_obligatorio` de cada entrada es el que exige el agente.

    Este es el test de deriva que de verdad importa en A6: el catálogo NO se
    copia en el evaluador, se declara entrada a entrada en el JSON. Si el
    agente añade mañana una cláusula obligatoria a MEDIA, aquí salta y el
    dataset se actualiza a mano, que es lo que se espera de un golden.
    """
    from backend.app.agents import agent_06_contratos as a06

    ds = load_golden_dataset("agent_06_contratos", "v1")
    for entrada in ds.entries:
        categoria = entrada.input["ens_category"]
        esperado = set(a06._BASE_CLAUSE_IDS)
        if categoria in ("MEDIA", "ALTA"):
            esperado |= set(a06._ENS_MEDIA_PLUS_CLAUSE_IDS)
        if categoria == "ALTA":
            esperado |= set(a06._ENS_ALTA_CLAUSE_IDS)
        declarado = set(entrada.expected_output.model_extra["catalogo_obligatorio"])
        assert declarado == esperado, (
            f"{entrada.id} ({categoria}): el dataset declara {sorted(declarado)} "
            f"y el agente exige {sorted(esperado)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2 · Registro y auto-consistencia
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("agente", AGENTES_D2)
def test_dataset_descubierto_y_registrado(agente: str):
    assert (agente, "v1") in list_available_datasets()
    assert agente in _AGENT_EVALUATORS
    assert agente in _AGENT_SYNTHETIC_OUTPUTS
    assert get_synthetic_output_builder(agente) is not None


@pytest.mark.parametrize("agente", AGENTES_D2)
def test_dataset_tiene_diez_entradas_y_los_umbrales_del_gate(agente: str):
    ds = load_golden_dataset(agente, "v1")
    assert len(ds.entries) == 10
    assert ds.regression_thresholds.pass_rate_warn_below == 0.8
    assert ds.regression_thresholds.pass_rate_alert_below == 0.6
    dificultades = [
        e.model_extra.get("dificultad") for e in ds.entries  # type: ignore[union-attr]
    ]
    # La mezcla es parte del diseño: sin casos que deban fallar, un dataset
    # sólo mide que el modelo sabe repetir lo fácil.
    assert dificultades.count("debe_fallar") >= 2
    assert dificultades.count("limite") >= 3


@pytest.mark.parametrize(
    "agente", AGENTES_D2 + ("deliverable_text_auditor",),
)
def test_auto_consistencia_dataset_evaluador(agente: str):
    """La salida sintética que el dataset declara TIENE que aprobar."""
    ds = load_golden_dataset(agente, "v1")
    evaluador = _AGENT_EVALUATORS[agente]
    fallos = []
    for entrada in ds.entries:
        resultado = evaluador(entrada, build_synthetic_output(agente, entrada))
        if not (resultado.passed and not resultado.skipped):
            fallos.append(f"{entrada.id}: {resultado.diff_summary}")
    assert not fallos, fallos


@pytest.mark.parametrize("agente", AGENTES_D2)
def test_sin_proveedor_la_entrada_se_salta_y_no_se_cuenta(agente: str):
    """`actual=None` es "no se pudo preguntar", no "el modelo falló"."""
    ds = load_golden_dataset(agente, "v1")
    resultado = _AGENT_EVALUATORS[agente](ds.entries[0], None)
    assert resultado.skipped is True
    assert resultado.passed is False
    assert resultado.skip_reason


@pytest.mark.parametrize("agente", AGENTES_D2)
def test_respuesta_sin_json_cuenta_como_fallo_no_como_salto(agente: str):
    """Si el modelo contesta prosa, la entrada FALLA. Tuvo su turno."""
    ds = load_golden_dataset(agente, "v1")
    sucia = {SALIDA_SIN_JSON: "Claro, con mucho gusto. Este documento parece..."}
    resultado = _AGENT_EVALUATORS[agente](ds.entries[0], sucia)
    assert resultado.passed is False
    assert resultado.skipped is False
    assert "no devolvió JSON" in resultado.diff_summary


@pytest.mark.parametrize("agente", AGENTES_D2)
def test_faltar_una_clave_obligatoria_es_fallo(agente: str):
    ds = load_golden_dataset(agente, "v1")
    entrada = ds.entries[0]
    salida = build_synthetic_output(agente, entrada)
    clave = _AGENT_EVALUATORS[agente].__globals__["_CLAVES_OBLIGATORIAS"][0]
    salida.pop(clave)
    resultado = _AGENT_EVALUATORS[agente](entrada, salida)
    assert resultado.passed is False
    assert clave in resultado.diff_summary


# ═══════════════════════════════════════════════════════════════════════════
# 3 · Cada evaluador sabe decir que no, por el motivo concreto
# ═══════════════════════════════════════════════════════════════════════════


def _entrada(agente: str, entry_id: str):
    ds = load_golden_dataset(agente, "v1")
    for e in ds.entries:
        if e.id == entry_id:
            return e
    raise AssertionError(f"no existe la entrada {entry_id} en {agente}")


def _mutar(agente: str, entry, **cambios: Any) -> dict:
    salida = copy.deepcopy(build_synthetic_output(agente, entry))
    salida.update(cambios)
    return salida


def test_a27_carpeta_equivocada_falla():
    entrada = _entrada("agent_27_clasificador", "a27-001")  # acta -> 01 Gobierno
    salida = _mutar(
        "agent_27_clasificador", entrada,
        suggested_folder_code="13", suggested_folder_name="Informes_Tecnicos",
    )
    resultado = ev27.agent_27_clasificador_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "el dataset acepta" in resultado.diff_summary


def test_a27_nombre_que_no_corresponde_al_codigo_falla():
    entrada = _entrada("agent_27_clasificador", "a27-001")
    salida = _mutar(
        "agent_27_clasificador", entrada, suggested_folder_name="Continuidad",
    )
    resultado = ev27.agent_27_clasificador_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "no corresponde al código" in resultado.diff_summary


def test_a27_adivinar_con_confianza_alta_sobre_un_fichero_equivocado_falla():
    """a27-009: el nombre promete una política y el contenido es otra cosa."""
    entrada = _entrada("agent_27_clasificador", "a27-009")
    salida = _mutar(
        "agent_27_clasificador", entrada,
        suggested_folder_code="06", suggested_folder_name="Normativa",
        confidence=0.93, alternative_folders=[], requires_human_review=False,
    )
    resultado = ev27.agent_27_clasificador_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "el dataset acepta" in resultado.diff_summary
    assert "banda curada" in resultado.diff_summary


def test_a27_falta_de_alternativa_en_caso_ambiguo_falla():
    entrada = _entrada("agent_27_clasificador", "a27-006")  # límite, exige 1 alt
    salida = _mutar("agent_27_clasificador", entrada, alternative_folders=[])
    resultado = ev27.agent_27_clasificador_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "alternativa" in resultado.diff_summary


def test_a27_contradiccion_del_modelo_se_anota_pero_no_suspende():
    """Confianza alta y bandera a true: producción lo repara, aquí se anota."""
    entrada = _entrada("agent_27_clasificador", "a27-001")
    salida = _mutar("agent_27_clasificador", entrada, requires_human_review=True)
    resultado = ev27.agent_27_clasificador_evaluator(entrada, salida)
    assert resultado.passed is True
    assert resultado.actual_summary["el_modelo_se_contradice"] is True


def test_a18_categoria_prohibida_falla():
    """a18-007: el cliente pide BÁSICA para una sede electrónica."""
    entrada = _entrada("agent_18_reunion", "a18-007")
    salida = _mutar("agent_18_reunion", entrada, categoria_ens="BASICA")
    resultado = ev18.agent_18_reunion_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "el dataset acepta" in resultado.diff_summary


def test_a18_complacencia_en_un_plazo_imposible_falla():
    """a18-005: tres semanas para una MEDIA desde cero no es "ajustada"."""
    entrada = _entrada("agent_18_reunion", "a18-005")
    salida = _mutar("agent_18_reunion", entrada, viabilidad_temporal="ajustada")
    resultado = ev18.agent_18_reunion_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "viabilidad_temporal" in resultado.diff_summary


def test_a18_inventarse_una_categoria_con_los_bloques_vacios_falla():
    entrada = _entrada("agent_18_reunion", "a18-009")
    salida = _mutar(
        "agent_18_reunion", entrada,
        categoria_ens="MEDIA", confianza_categoria=0.85,
    )
    resultado = ev18.agent_18_reunion_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "banda curada" in resultado.diff_summary


def test_a18_horas_que_no_solapan_la_banda_fallan():
    entrada = _entrada("agent_18_reunion", "a18-001")  # banda 40-110
    salida = _mutar(
        "agent_18_reunion", entrada,
        horas_marcos_estimadas={"min": 300, "max": 400, "rationale": "x"},
    )
    resultado = ev18.agent_18_reunion_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "no solapa" in resultado.diff_summary


def test_a18_enumerado_invalido_falla():
    entrada = _entrada("agent_18_reunion", "a18-001")
    salida = _mutar("agent_18_reunion", entrada, madurez_actual="L9")
    resultado = ev18.agent_18_reunion_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "fuera del enumerado" in resultado.diff_summary


def test_a06_dar_por_presente_una_clausula_ausente_falla():
    """a06-002: el contrato de desarrollo no tiene DPA por ningún lado."""
    entrada = _entrada("agent_06_contratos", "a06-002")
    salida = build_synthetic_output("agent_06_contratos", entrada)
    for item in salida["mandatory_clauses_check"]:
        if item["clause_id"] == "art_28_dpa":
            item["present"], item["quality"] = True, "completo"
    resultado = ev06.agent_06_contratos_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "art_28_dpa" in resultado.diff_summary


def test_a06_dar_por_completa_una_clausula_que_no_cumple_falla():
    """a06-010: auditoría cada tres años, 90 días de preaviso, a su costa."""
    entrada = _entrada("agent_06_contratos", "a06-010")
    salida = build_synthetic_output("agent_06_contratos", entrada)
    for item in salida["mandatory_clauses_check"]:
        if item["clause_id"] == "derecho_auditoria":
            item["quality"] = "completo"
    resultado = ev06.agent_06_contratos_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "la da por completa" in resultado.diff_summary


def test_a06_checklist_incompleto_falla():
    entrada = _entrada("agent_06_contratos", "a06-004")  # ALTA: 13 cláusulas
    salida = build_synthetic_output("agent_06_contratos", entrada)
    salida["mandatory_clauses_check"] = salida["mandatory_clauses_check"][:5]
    resultado = ev06.agent_06_contratos_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "no cubre" in resultado.diff_summary


def test_a06_puntuar_alto_un_contrato_de_otra_cosa_falla():
    """a06-008: el texto es un contrato de suministro eléctrico."""
    entrada = _entrada("agent_06_contratos", "a06-008")
    salida = _mutar(
        "agent_06_contratos", entrada,
        compliance_score=78, compliance_level="conforme",
    )
    resultado = ev06.agent_06_contratos_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "banda curada" in resultado.diff_summary
    assert "el dataset acepta" in resultado.diff_summary


def test_a06_no_ver_el_hueco_sectorial_de_sanidad_falla():
    entrada = _entrada("agent_06_contratos", "a06-006")
    salida = _mutar("agent_06_contratos", entrada, sector_specific_gaps=[])
    resultado = ev06.agent_06_contratos_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "huecos sectoriales" in resultado.diff_summary


def test_a06_adenda_vacia_falla():
    entrada = _entrada("agent_06_contratos", "a06-001")
    salida = _mutar("agent_06_contratos", entrada, addendum_text="")
    resultado = ev06.agent_06_contratos_evaluator(entrada, salida)
    assert resultado.passed is False
    assert "addendum_text" in resultado.diff_summary
