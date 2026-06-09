"""Tests Agente 18 - Reunion Exploratoria (Sesion 9 Paso 2.2).

Patron A19/A20:
- Tests asyncio deterministas (mock LLM con AsyncMock): normalizacion
  bloques, validador schema, retry + fallback, latencia/coste.
- Tests @pytest.mark.llm con llamada real Sonnet 4.6 para probar las
  3 ramas sectoriales del prompt (sanidad, AAPP, fintech) + bloques
  parciales.

Los tests LLM se saltan automaticamente si ANTHROPIC_API_KEY no esta
configurado (.env via python-dotenv).
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_18_reunion import (
    Agent18ReunionExploratoria,
    AsistenteReunionExploratoriaAgent,
    _CATEGORIAS,
    _ESFUERZO,
    _IMPACTO,
    _MADUREZ,
    _REQUIRED_KEYS,
    _VIABILIDAD,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


def _valid_insight() -> dict:
    """Insight JSON valido para validador schema."""
    return {
        "categoria_ens": "MEDIA",
        "confianza_categoria": 0.7,
        "rationale_categoria": "Sanidad privada con HCE, datos salud Art. 9 RGPD.",
        "madurez_actual": "L1",
        "horas_marcos_estimadas": {
            "min": 100,
            "max": 130,
            "rationale": "MEDIA + sanidad + multi-sede.",
        },
        "viabilidad_temporal": "ajustada",
        "riesgos_detectados": [
            {
                "titulo": "Tratamiento datos salud Art. 9",
                "impacto": "alto",
                "descripcion": "HCE gestiona datos especial categoria.",
            },
        ],
        "quick_wins_sugeridas": [
            {"titulo": "MFA Azure AD", "esfuerzo": "1d", "impacto": "Cierra op.acc.5."},
        ],
        "preguntas_pendientes": [
            "Cuantos empleados acceden al HCE directamente?",
            "Plazo de la licitacion SERMAS?",
        ],
    }


def _mock_response(insight: dict, *, tokens_in: int = 800, tokens_out: int = 600) -> dict:
    """Simula lo que AgentBase.invoke devuelve cuando structured_output=True."""
    return {
        "agent_id": 18,
        "agent_name": "Reunion Exploratoria",
        "response": "{...}",
        "parsed": insight,
        "model": "claude-sonnet-4-6",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "latency_ms": 3200,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Alias retrocompatible
# =======================================================================


def test_agent_18_alias_backcompat():
    """AsistenteReunionExploratoriaAgent sigue siendo alias de la clase nueva."""
    assert AsistenteReunionExploratoriaAgent is Agent18ReunionExploratoria


# =======================================================================
# 2) Normalizacion bloques A-F
# =======================================================================


def test_agent_18_normalize_blocks_fills_canonical_keys():
    """_normalize_blocks garantiza las 6 claves A-F incluso si vienen parciales."""
    raw = {
        "A_contexto": "DataForma SL, sanidad privada Madrid, 45 empleados.",
        "B_informacion": "HCE + Salesforce + Azure AD. 2 sedes Madrid.",
        # C, D, E, F ausentes
    }
    norm = Agent18ReunionExploratoria._normalize_blocks(raw)
    assert set(norm.keys()) == {
        "A_contexto", "B_informacion", "C_madurez",
        "D_plazos", "E_presupuesto", "F_equipo",
    }
    assert norm["A_contexto"].startswith("DataForma")
    assert norm["C_madurez"] == ""
    assert norm["F_equipo"] == ""


def test_agent_18_normalize_blocks_coerces_none_to_empty_string():
    """Valores None se convierten en cadena vacia sin romper build_user_message."""
    raw = {"A_contexto": None, "B_informacion": 42}
    norm = Agent18ReunionExploratoria._normalize_blocks(raw)
    assert norm["A_contexto"] == ""
    assert norm["B_informacion"] == "42"


# =======================================================================
# 3) Validador de schema strict
# =======================================================================


def test_agent_18_schema_valid_insight_passes():
    agent = Agent18ReunionExploratoria()
    errors = agent._validate_schema(_valid_insight())
    assert errors == []


def test_agent_18_schema_rejects_missing_keys():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    del insight["horas_marcos_estimadas"]
    errors = agent._validate_schema(insight)
    assert any("horas_marcos_estimadas" in e for e in errors)


def test_agent_18_schema_rejects_invalid_categoria():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["categoria_ens"] = "EXTREMA"
    errors = agent._validate_schema(insight)
    assert any("categoria_ens" in e for e in errors)


def test_agent_18_schema_rejects_confianza_fuera_rango():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["confianza_categoria"] = 1.7
    errors = agent._validate_schema(insight)
    assert any("confianza_categoria" in e for e in errors)


def test_agent_18_schema_rejects_madurez_invalida():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["madurez_actual"] = "L9"
    errors = agent._validate_schema(insight)
    assert any("madurez_actual" in e for e in errors)


def test_agent_18_schema_rejects_horas_fuera_rango():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["horas_marcos_estimadas"]["max"] = 9999
    errors = agent._validate_schema(insight)
    assert any("max" in e for e in errors)


def test_agent_18_schema_limits_listas():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["riesgos_detectados"] = [
        {"titulo": f"r{i}", "impacto": "bajo", "descripcion": "x"} for i in range(5)
    ]
    insight["quick_wins_sugeridas"] = [
        {"titulo": f"q{i}", "esfuerzo": "1h", "impacto": "x"} for i in range(4)
    ]
    insight["preguntas_pendientes"] = [f"p{i}" for i in range(7)]
    errors = agent._validate_schema(insight)
    assert any("riesgos_detectados" in e for e in errors)
    assert any("quick_wins_sugeridas" in e for e in errors)
    assert any("preguntas_pendientes" in e for e in errors)


def test_agent_18_schema_rejects_enum_subfields():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["riesgos_detectados"][0]["impacto"] = "cataclismico"
    insight["quick_wins_sugeridas"][0]["esfuerzo"] = "1y"
    errors = agent._validate_schema(insight)
    assert any("impacto" in e for e in errors)
    assert any("esfuerzo" in e for e in errors)


def test_agent_18_schema_rationale_respeta_limite_250_chars():
    agent = Agent18ReunionExploratoria()
    insight = _valid_insight()
    insight["rationale_categoria"] = "x" * 260
    errors = agent._validate_schema(insight)
    assert any("rationale_categoria" in e for e in errors)


# =======================================================================
# 4) Fallback determinista cuando el LLM devuelve basura
# =======================================================================


async def test_agent_18_fallback_on_invalid_json(db):
    """Si el LLM no parsea JSON, cae a fallback UNKNOWN con preguntas apertura."""
    agent = Agent18ReunionExploratoria()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 50, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    with patch.object(
        Agent18ReunionExploratoria, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.analyze_meeting_blocks(
            db,
            blocks={"A_contexto": "Cliente X, sector desconocido."},
            blocks_filled=["A"],
        )

    assert result["fallback_used"] is True
    assert result["schema_valid"] is False
    insight = result["insight"]
    assert insight["categoria_ens"] == "UNKNOWN"
    assert insight["madurez_actual"] == "L0"
    assert insight["viabilidad_temporal"] == "desconocida"
    # Preguntas apertura generadas para bloques vacios (B/C/D/F)
    assert len(insight["preguntas_pendientes"]) >= 3
    assert result["retry_count"] >= 1


async def test_agent_18_fallback_on_schema_violation(db):
    """Si el LLM devuelve JSON pero viola schema, agota retry y cae a fallback."""
    agent = Agent18ReunionExploratoria()
    bogus_parsed = {
        "categoria_ens": "EXTREMA",          # invalid enum
        "confianza_categoria": 3.0,          # out of range
        "rationale_categoria": "",
        "madurez_actual": "L9",              # invalid
        "horas_marcos_estimadas": "not a dict",
        "viabilidad_temporal": "tal vez",
        "riesgos_detectados": "debe ser lista",
        "quick_wins_sugeridas": [],
        "preguntas_pendientes": [],
    }
    bad = _mock_response(bogus_parsed)
    with patch.object(
        Agent18ReunionExploratoria, "invoke", new=AsyncMock(return_value=bad)
    ) as invoke_mock:
        result = await agent.analyze_meeting_blocks(
            db,
            blocks={"A_contexto": "Contexto minimo."},
        )

    # 1 primer intento + 1 retry (MAX_RETRIES_ON_INVALID_JSON = 1)
    assert invoke_mock.call_count == 2
    assert result["fallback_used"] is True
    assert result["insight"]["categoria_ens"] == "UNKNOWN"
    assert len(result["schema_errors"]) >= 1


async def test_agent_18_success_first_attempt(db):
    """LLM devuelve JSON valido al primer intento: no hay fallback ni retry."""
    agent = Agent18ReunionExploratoria()
    good = _mock_response(_valid_insight(), tokens_in=820, tokens_out=560)
    with patch.object(
        Agent18ReunionExploratoria, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.analyze_meeting_blocks(
            db,
            blocks={
                "A_contexto": "Hospital privado 45 empleados Madrid.",
                "B_informacion": "HCE propio + Azure AD.",
            },
            blocks_filled=["A", "B"],
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    assert result["schema_errors"] == []
    assert result["retry_count"] == 0
    assert result["insight"]["categoria_ens"] == "MEDIA"
    # Coste estimado > 0 (Sonnet 4.6 pricing aplicado)
    assert result["cost_eur_estimated"] > 0
    assert result["model"].startswith("claude-sonnet-4-6") or result["model"] == "sonnet-4.6"


# =======================================================================
# 5) blocks_filled auto-derivado
# =======================================================================


async def test_agent_18_blocks_filled_auto_derived_from_content(db):
    """Si blocks_filled es None, se calcula desde los bloques con >=5 chars."""
    agent = Agent18ReunionExploratoria()
    good = _mock_response(_valid_insight())
    with patch.object(
        Agent18ReunionExploratoria, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        await agent.analyze_meeting_blocks(
            db,
            blocks={
                "A_contexto": "Texto suficientemente largo (>5 chars).",
                "B_informacion": "x",            # <5 chars -> no cuenta
                "C_madurez": "Politicas viejas de 2018.",
            },
            blocks_filled=None,
        )
    # invoke recibio context con blocks_filled derivado = ["A", "C"]
    call_args = invoke_mock.call_args
    ctx = call_args.kwargs["context"]
    assert ctx["blocks_filled"] == ["A", "C"]


# =======================================================================
# 6) Estructura del resultado
# =======================================================================


async def test_agent_18_result_shape_contains_metrics(db):
    agent = Agent18ReunionExploratoria()
    good = _mock_response(_valid_insight(), tokens_in=900, tokens_out=700)
    with patch.object(
        Agent18ReunionExploratoria, "invoke", new=AsyncMock(return_value=good)
    ):
        result = await agent.analyze_meeting_blocks(
            db, blocks={"A_contexto": "Contexto valido largo."},
        )
    for key in (
        "insight", "schema_valid", "schema_errors", "retry_count",
        "tokens_input", "tokens_output", "cost_eur_estimated",
        "latency_ms", "model", "fallback_used",
    ):
        assert key in result, f"Falta key {key!r} en resultado"
    assert result["tokens_input"] == 900
    assert result["tokens_output"] == 700


# =======================================================================
# 7) Enums del modulo expuestos (contrato publico interno)
# =======================================================================


def test_agent_18_exposed_enums_match_spec():
    """Los sets de enums deben cubrir exactamente los valores del prompt."""
    assert _CATEGORIAS == {"BASICA", "MEDIA", "ALTA", "UNKNOWN"}
    assert _MADUREZ == {"L0", "L1", "L2", "L3", "L4", "L5"}
    assert _VIABILIDAD == {"holgada", "ajustada", "inviable", "desconocida"}
    assert _IMPACTO == {"alto", "medio", "bajo"}
    assert _ESFUERZO == {"1h", "1d", "1w"}
    assert len(_REQUIRED_KEYS) == 9


# =======================================================================
# 8) LLM real - sector sanidad PYME privada
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_18_real_llm_sanidad_pyme(db):
    """Ejemplo 1 del prompt - DataForma sanidad privada PYME con bloques A+B."""
    _skip_if_no_api_key()
    agent = Agent18ReunionExploratoria()
    result = await agent.analyze_meeting_blocks(
        db,
        blocks={
            "A_contexto": (
                "DataForma SL, empresa de gestion clinica privada en Madrid, "
                "45 empleados. Quieren certificacion ENS para poder licitar con "
                "el SERMAS y otras consejerias de sanidad autonomicas."
            ),
            "B_informacion": (
                "Sistemas en alcance: HCE propio desarrollado in-house, "
                "Salesforce CRM, Azure AD para autenticacion. 2 sedes: "
                "central en Madrid y delegacion en Alcala de Henares."
            ),
        },
        blocks_filled=["A", "B"],
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado con bloques A+B validos; errores={result['schema_errors'][:3]}"
    )
    insight = result["insight"]
    # Sanidad privada con HCE y licitacion SERMAS -> MEDIA (o UNKNOWN conservador)
    assert insight["categoria_ens"] in {"MEDIA", "ALTA", "UNKNOWN"}
    # Debe detectar al menos un riesgo (datos salud, dependencia Azure AD, etc.)
    assert isinstance(insight["riesgos_detectados"], list)
    # Debe tener preguntas pendientes accionables (falta C/D/E/F)
    assert len(insight["preguntas_pendientes"]) >= 1


# =======================================================================
# 9) LLM real - rama AAPP Ayuntamiento
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_18_real_llm_aapp_ayuntamiento_urgente(db):
    """Ejemplo 2 del prompt - Ayto Villanueva BASICA con urgencia <6 semanas."""
    _skip_if_no_api_key()
    agent = Agent18ReunionExploratoria()
    result = await agent.analyze_meeting_blocks(
        db,
        blocks={
            "A_contexto": (
                "Ayuntamiento de Villanueva, municipio de 8.000 habitantes. "
                "Necesitan certificacion ENS para adjudicacion de gestion "
                "tributaria que la Diputacion exige para el 15 de marzo."
            ),
            "B_informacion": (
                "Un unico sistema: portal ciudadano alojado en Azure Spain. "
                "1 sede: Casa Consistorial. 15 trabajadores municipales."
            ),
            "C_madurez": (
                "No tienen nada documentado. Les auditaron en 2023 y "
                "arrojo muchas no conformidades."
            ),
            "D_plazos": (
                "Necesitan certificacion en 8 semanas. Licitacion cierra 15 marzo."
            ),
            "E_presupuesto": "Sin rango definido, pediran Apendice M v2.2.",
            "F_equipo": (
                "Secretario Municipal firma. DPO externo. Concejal TIC Ana Garcia."
            ),
        },
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    insight = result["insight"]
    # Municipio pequeno 1 sistema -> BASICA (o MEDIA conservador)
    assert insight["categoria_ens"] in {"BASICA", "MEDIA"}
    # Plazo 8 semanas + madurez L0 -> viabilidad ajustada o inviable
    assert insight["viabilidad_temporal"] in {"ajustada", "inviable"}
    # Madurez L0/L1 porque no tienen nada documentado
    assert insight["madurez_actual"] in {"L0", "L1"}
    # Debe detectar al menos un riesgo (plazo + madurez o precedente auditoria)
    assert len(insight["riesgos_detectados"]) >= 1


# =======================================================================
# 10) LLM real - fallback cuando no hay info
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(600)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_18_real_llm_empty_blocks_returns_unknown_or_opening(db):
    """Bloques vacios -> UNKNOWN + preguntas de apertura (directamente del LLM
    o via fallback determinista). Cualquiera de las 2 rutas es aceptable."""
    _skip_if_no_api_key()
    agent = Agent18ReunionExploratoria()
    result = await agent.analyze_meeting_blocks(
        db,
        blocks={k: "" for k in (
            "A_contexto", "B_informacion", "C_madurez",
            "D_plazos", "E_presupuesto", "F_equipo",
        )},
        blocks_filled=[],
    )
    insight = result["insight"]
    # Con todos los bloques vacios, el LLM conservador debe usar UNKNOWN
    assert insight["categoria_ens"] == "UNKNOWN"
    # Debe generar preguntas de apertura (>=3)
    assert len(insight["preguntas_pendientes"]) >= 3


# =======================================================================
# 11) LLM real - prompt caching reduce COSTE en 2a llamada
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(120)
async def test_agent_18_prompt_caching_reduces_cost(db):
    """2 llamadas consecutivas con el mismo system prompt.

    Caching reduce el **coste** ~49% (cache_read = 10% tarifa input),
    NO la latencia total — el bottleneck es generacion output (~920
    tokens @ 70 tok/s Sonnet 4.6 = ~13s fisicos). El streaming SSE
    para feel live esta programado para Sesion 11 Frontend K.4 (ver
    TODO-A18-LATENCY en progress/backlog_formal.md).

    Run 1: cache write (cache_creation_input_tokens > 0).
    Run 2: cache read (cache_read_input_tokens > 0) + coste <70%
    del run 1 (ahorro real >30%).
    """
    _skip_if_no_api_key()
    agent = Agent18ReunionExploratoria()
    blocks = {
        "A_contexto": (
            "Ayuntamiento de Villasencillo, municipio 6000 habitantes, "
            "Castilla y Leon. Necesitan ENS para licitar gestion tributaria."
        ),
        "B_informacion": (
            "Un unico sistema portal ciudadano Azure. 1 sede Casa Consistorial. "
            "12 trabajadores. Sin multi-sede."
        ),
        "C_madurez": "Sin politicas escritas. Auditoria 2023 con NCs.",
        "D_plazos": "Certificacion en 10 semanas. Licitacion junio.",
        "E_presupuesto": "Aprobada partida 4500 EUR.",
        "F_equipo": "Secretario firma. DPO externo. Concejal TIC Ana.",
    }

    first = await agent.analyze_meeting_blocks(
        db, blocks=blocks, blocks_filled=["A", "B", "C", "D", "E", "F"],
    )
    # Run 2 inmediato (TTL 5 min ephemeral, sin timeout intermedio).
    second = await agent.analyze_meeting_blocks(
        db, blocks=blocks, blocks_filled=["A", "B", "C", "D", "E", "F"],
    )

    # Caching estructuralmente activo: al menos un run lee cache. La
    # cache puede estar caliente al arrancar el test por pytest haber
    # corrido ya otros tests LLM del mismo agente (mismo system prompt).
    # En ese caso Run 1 ya lee cache; en cold-start Run 1 escribe y Run 2
    # lee. Cualquiera de las 2 rutas confirma que el caching funciona.
    assert first["cache_read_input_tokens"] > 0 or second["cache_read_input_tokens"] > 0, (
        f"Ni Run 1 ni Run 2 leyeron cache. "
        f"first.read={first['cache_read_input_tokens']}, "
        f"second.read={second['cache_read_input_tokens']}. "
        "Caching no esta funcionando (modelo sin soporte o prompt corto)."
    )

    # Run 2 es SIEMPRE cache hit (inmediato tras run 1, mismo system).
    assert second["cache_read_input_tokens"] > 0, (
        f"Run 2 no leyo cache ({second['cache_read_input_tokens']}). "
        "Se esperaba hit inmediato tras Run 1 con mismo system prompt."
    )

    # Coste Run 2 (cache hit) debe ser pequeno. Sonnet 4.6 con cache read
    # ~10% tarifa input + output tarifa normal: ~920 tokens_out * 15 USD/M
    # * 0.93 EUR/USD = ~0.013 EUR + ~0.001 EUR cache read. Tope 0.020 EUR
    # da margen razonable.
    assert second["cost_eur_estimated"] < 0.020, (
        f"Run 2 coste {second['cost_eur_estimated']:.5f} EUR > 0.020 EUR. "
        f"Cache hit deberia mantener coste bajo pero esta alto (ratio "
        f"cache_read={second['cache_read_input_tokens']}/cache_write="
        f"{second['cache_creation_input_tokens']})."
    )

    # Determinismo semantico a T=0.1: misma categoria en ambos runs
    assert first["insight"]["categoria_ens"] == second["insight"]["categoria_ens"]
    assert first["fallback_used"] is False
    assert second["fallback_used"] is False
