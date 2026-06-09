"""Tests Agente 17 - Cualificador Comercial (Sesion 9 Paso 2.3).

Patron A18/A20:
- Tests deterministas (mock LLM con AsyncMock): fallback scoring,
  schema validator, casos A/B/C con mock, persistencia opcional.
- Tests @pytest.mark.llm con llamada real Sonnet 4.6 para probar los
  3 ejemplos few-shot (sanidad MEDIA, Ayto BASICA, empresa explora).
- Test caching (@llm) valida cache_read > 0 run 2 + coste reducido.

Los tests LLM se saltan automaticamente si ANTHROPIC_API_KEY no esta
configurado (.env via python-dotenv).
"""
from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from backend.app.agents.agent_17_cualificador import (
    Agent17CualificadorComercial,
    CualificadorComercialAgent,
    _CLASSIFICATIONS,
    _DIMENSION_KEYS,
    _NEXT_ACTIONS,
    _PRIORITIES,
    _REQUIRED_KEYS,
    _WHEN_VALUES,
)
from backend.app.database import set_tenant_context
from backend.tests.conftest import _admin_setup


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


def _ideal_lead_inputs() -> tuple[dict, dict]:
    ctx = {
        "company_name": "Hospital Sanitas Pro",
        "company_sector": "sanidad",
        "company_size": "mediana 180 empleados",
        "origin": "referencia",
    }
    ans = {
        "contract_status": "adjudicado",
        "ens_category_expected": "MEDIA",
        "deadline": "3m",
        "sponsor": "claro",
        "budget": "asignado",
        "tech_team": "externalizado",
        "existing_frameworks": ["RGPD"],
        "lead_quality": "calido",
    }
    return ctx, ans


def _weak_lead_inputs() -> tuple[dict, dict]:
    ctx = {
        "company_name": "Grupo TecSA",
        "company_sector": "servicios tecnologicos",
        "company_size": "grande 800 empleados",
        "origin": "evento",
    }
    ans = {
        "contract_status": "explorando",
        "ens_category_expected": "desconocida",
        "deadline": "sin_plazo",
        "sponsor": "sin_identificar",
        "budget": "ninguno",
        "tech_team": "propio",
        "existing_frameworks": ["ISO27001"],
        "lead_quality": "frio",
    }
    return ctx, ans


def _valid_llm_response(qualification: dict, *, tokens_in: int = 1500, tokens_out: int = 500) -> dict:
    """Simula lo que AgentBase.invoke devuelve con structured_output=True."""
    return {
        "agent_id": 17,
        "agent_name": "Cualificador Comercial",
        "response": "{...}",
        "parsed": qualification,
        "model": "claude-sonnet-4-6",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 3000,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Alias retrocompat + enums expuestos
# =======================================================================


def test_agent_17_alias_backcompat():
    assert CualificadorComercialAgent is Agent17CualificadorComercial


def test_agent_17_enums_match_spec():
    assert _CLASSIFICATIONS == {"A", "B", "C", "DESCARTAR"}
    assert _PRIORITIES == {"ardiendo", "caliente", "tibio", "frio"}
    assert "agendar_exploratoria" in _NEXT_ACTIONS
    assert "descartar" in _NEXT_ACTIONS
    assert "esta_semana" in _WHEN_VALUES
    assert "en_3_meses" in _WHEN_VALUES
    assert len(_REQUIRED_KEYS) == 8
    assert len(_DIMENSION_KEYS) == 6


# =======================================================================
# 2) Fallback determinista - lead ideal puntua A
# =======================================================================


async def test_agent_17_empty_answers_fallback(db):
    """Sin respuestas criticas (todo en desconocido/ninguno) cae a DESCARTAR."""
    agent = Agent17CualificadorComercial()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 50, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    ctx = {"company_name": "Empty Co", "company_sector": "desconocido", "origin": "frio"}
    ans = {
        "contract_status": "desconocido",
        "deadline": "sin_plazo",
        "sponsor": "sin_identificar",
        "budget": "ninguno",
        "ens_category_expected": "desconocida",
        "tech_team": "ninguno",
        "existing_frameworks": [],
        "lead_quality": "frio",
    }
    with patch.object(
        Agent17CualificadorComercial, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.qualify_lead(
            db, lead_context=ctx, qualification_answers=ans,
        )

    assert result["fallback_used"] is True
    qual = result["qualification"]
    assert qual["classification"] in {"C", "DESCARTAR"}
    assert qual["priority"] in {"frio", "tibio"}
    assert 0 <= qual["lead_score"] <= 40
    # Debe detectar al menos un red flag (sin presupuesto / sin sponsor)
    assert len(qual["red_flags"]) >= 1


# =======================================================================
# 3) Success path con mock - lead ideal A
# =======================================================================


async def test_agent_17_ideal_lead_mocked_scores_A(db):
    """LLM devuelve JSON valido clasificando A en un lead ideal."""
    agent = Agent17CualificadorComercial()
    good_qual = {
        "lead_score": 85,
        "classification": "A",
        "priority": "caliente",
        "recommendation": "Lead ardiendo: agendar exploratoria 45 min esta semana.",
        "dimension_scores": {
            "urgencia": 85, "presupuesto": 90, "sponsor_power": 90,
            "fit_producto": 85, "madurez_ens": 40, "calidad_lead": 85,
        },
        "next_actions": [
            {"action": "agendar_exploratoria", "when": "esta_semana"},
        ],
        "red_flags": [],
        "rationale": "Contrato adjudicado + sponsor claro + presupuesto asignado.",
    }
    good = _valid_llm_response(good_qual)
    ctx, ans = _ideal_lead_inputs()
    with patch.object(
        Agent17CualificadorComercial, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.qualify_lead(
            db, lead_context=ctx, qualification_answers=ans,
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    assert result["qualification"]["classification"] == "A"
    assert result["qualification"]["lead_score"] == 85


# =======================================================================
# 4) Mock - lead debil puntua C
# =======================================================================


async def test_agent_17_weak_lead_mocked_scores_C(db):
    agent = Agent17CualificadorComercial()
    qual = {
        "lead_score": 25,
        "classification": "C",
        "priority": "frio",
        "recommendation": "Lead educativo: enviar contenido ENS+ISO esta semana.",
        "dimension_scores": {
            "urgencia": 15, "presupuesto": 5, "sponsor_power": 10,
            "fit_producto": 55, "madurez_ens": 40, "calidad_lead": 30,
        },
        "next_actions": [
            {"action": "enviar_material_educativo", "when": "esta_semana"},
            {"action": "seguimiento_dias", "when": "en_1_mes"},
        ],
        "red_flags": [
            "Sin presupuesto asignado: baja probabilidad de cierre a corto plazo.",
            "Sin sponsor identificado: venta compleja.",
        ],
        "rationale": "Explorando + sin presupuesto + sin sponsor = nurture por email.",
    }
    good = _valid_llm_response(qual)
    ctx, ans = _weak_lead_inputs()
    with patch.object(
        Agent17CualificadorComercial, "invoke", new=AsyncMock(return_value=good)
    ):
        result = await agent.qualify_lead(
            db, lead_context=ctx, qualification_answers=ans,
        )

    assert result["fallback_used"] is False
    assert result["qualification"]["classification"] == "C"
    assert result["qualification"]["priority"] == "frio"


# =======================================================================
# 5) Schema strict validation
# =======================================================================


@pytest.mark.parametrize(
    "corruption,expected_error_substring",
    [
        ({"lead_score": 150}, "lead_score"),
        ({"classification": "X"}, "classification"),
        ({"priority": "hirviendo"}, "priority"),
        ({"recommendation": "x" * 260}, "recommendation"),
        ({"dimension_scores": {}}, "dimension_scores"),
        ({"next_actions": [{"action": "bogus", "when": "hoy"}]}, "next_actions"),
        ({"next_actions": [{"action": "agendar_exploratoria", "when": "nunca"}]}, "when"),
        ({"red_flags": ["x" * 210]}, "red_flags"),
    ],
)
def test_agent_17_schema_strict_validation(corruption, expected_error_substring):
    agent = Agent17CualificadorComercial()
    base = {
        "lead_score": 75,
        "classification": "A",
        "priority": "caliente",
        "recommendation": "Base rec.",
        "dimension_scores": {
            "urgencia": 80, "presupuesto": 70, "sponsor_power": 80,
            "fit_producto": 70, "madurez_ens": 50, "calidad_lead": 70,
        },
        "next_actions": [{"action": "agendar_exploratoria", "when": "esta_semana"}],
        "red_flags": [],
        "rationale": "Base.",
    }
    base.update(corruption)
    errors = agent._validate_schema(base)
    assert any(expected_error_substring in e for e in errors), (
        f"No aparece '{expected_error_substring}' en {errors}"
    )


def test_agent_17_schema_coherence_classification_vs_score():
    """Classification A con score 30 debe detectarse como incoherente."""
    agent = Agent17CualificadorComercial()
    incoherent = {
        "lead_score": 30,
        "classification": "A",     # <- inconsistente
        "priority": "caliente",
        "recommendation": "test",
        "dimension_scores": {k: 50 for k in _DIMENSION_KEYS},
        "next_actions": [{"action": "agendar_exploratoria", "when": "hoy"}],
        "red_flags": [],
        "rationale": "test",
    }
    errors = agent._validate_schema(incoherent)
    assert any("incoherente" in e for e in errors)


# =======================================================================
# 6) Persistencia opcional en leads
# =======================================================================


async def _seed_lead(db) -> uuid.UUID:
    lead_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO leads (id, empresa_nombre, empresa_cif, sector, estado, created_at) "
                "VALUES (:id, 'Lead Test', :cif, 'sanidad', 'nuevo', now())"
            ),
            {"id": str(lead_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"},
        )
    await db.flush()
    return lead_id


async def test_agent_17_persists_to_lead_when_id_given(db):
    lead_id = await _seed_lead(db)
    await set_tenant_context(db)
    agent = Agent17CualificadorComercial()
    qual = {
        "lead_score": 78,
        "classification": "A",
        "priority": "caliente",
        "recommendation": "Test rec",
        "dimension_scores": {k: 70 for k in _DIMENSION_KEYS},
        "next_actions": [{"action": "agendar_exploratoria", "when": "esta_semana"}],
        "red_flags": [],
        "rationale": "Test",
    }
    good = _valid_llm_response(qual)
    ctx, ans = _ideal_lead_inputs()
    with patch.object(
        Agent17CualificadorComercial, "invoke", new=AsyncMock(return_value=good)
    ):
        await agent.qualify_lead(
            db, lead_context=ctx, qualification_answers=ans, lead_id=lead_id,
        )

    # Verificar que el Lead se actualizo
    async with _admin_setup(db):
        row = (await db.execute(
            text("SELECT lead_score, clasificacion_abc, estado FROM leads WHERE id = :id"),
            {"id": str(lead_id)},
        )).fetchone()

    assert row is not None
    assert float(row[0]) == 78.0
    assert row[1] == "A"
    assert row[2] == "cualificando"


# =======================================================================
# 7) LLM real - lead ideal sanidad MEDIA puntua A
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_17_ideal_sanidad_media_real_llm(db):
    """Ejemplo 1 del prompt: hospital sanidad MEDIA adjudicado 3m."""
    _skip_if_no_api_key()
    agent = Agent17CualificadorComercial()
    ctx, ans = _ideal_lead_inputs()
    result = await agent.qualify_lead(
        db, lead_context=ctx, qualification_answers=ans,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    qual = result["qualification"]
    # Lead ideal: esperamos A (70-100) o B alto (60-69)
    assert qual["classification"] in {"A", "B"}
    assert qual["lead_score"] >= 60
    assert qual["priority"] in {"ardiendo", "caliente", "tibio"}
    # Dimension presupuesto y sponsor deben ser altas
    assert qual["dimension_scores"]["presupuesto"] >= 70
    assert qual["dimension_scores"]["sponsor_power"] >= 70
    # Debe proponer agendar exploratoria como primera accion
    assert qual["next_actions"][0]["action"] == "agendar_exploratoria"


# =======================================================================
# 8) LLM real - lead debil explora sin presupuesto puntua C
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_17_weak_exploring_real_llm(db):
    """Ejemplo 3 del prompt: grupo grande explorando sin presupuesto."""
    _skip_if_no_api_key()
    agent = Agent17CualificadorComercial()
    ctx, ans = _weak_lead_inputs()
    result = await agent.qualify_lead(
        db, lead_context=ctx, qualification_answers=ans,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    qual = result["qualification"]
    # Lead debil: esperamos C (20-39) o DESCARTAR (0-19)
    assert qual["classification"] in {"C", "DESCARTAR"}
    assert qual["lead_score"] < 40
    # Priority debe ser frio (o tibio en el peor caso)
    assert qual["priority"] in {"frio", "tibio"}
    # Presupuesto y sponsor muy bajos
    assert qual["dimension_scores"]["presupuesto"] <= 20
    assert qual["dimension_scores"]["sponsor_power"] <= 30
    # Al menos 1 red flag
    assert len(qual["red_flags"]) >= 1


# =======================================================================
# 9) LLM real - prompt caching reduce coste en 2a llamada
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(120)
async def test_agent_17_prompt_caching_reduces_cost(db):
    """2 llamadas consecutivas del mismo agente: run 2 debe leer cache."""
    _skip_if_no_api_key()
    agent = Agent17CualificadorComercial()
    ctx, ans = _ideal_lead_inputs()

    first = await agent.qualify_lead(
        db, lead_context=ctx, qualification_answers=ans,
    )
    # Run 2 inmediato (TTL 5 min ephemeral).
    second = await agent.qualify_lead(
        db, lead_context=ctx, qualification_answers=ans,
    )

    # Cache funcional: al menos uno de los 2 lee cache (run 1 puede
    # estar ya caliente si los tests previos cachearon el mismo
    # system prompt — A17 tiene su propio prompt, pero por si acaso).
    assert first["cache_read_input_tokens"] > 0 or second["cache_read_input_tokens"] > 0, (
        f"Ni run 1 ni run 2 leyeron cache. "
        f"first.read={first['cache_read_input_tokens']} second.read={second['cache_read_input_tokens']}."
    )
    # Run 2 debe hacer cache hit inmediato.
    assert second["cache_read_input_tokens"] > 0

    # Coste run 2 bajo. Output A17 ~500 tokens * 15 USD/M * 0.93 =
    # ~0.007 EUR + cache read ~0.0006 EUR. Tope 0.015 EUR holgado.
    assert second["cost_eur_estimated"] < 0.015, (
        f"Run 2 coste {second['cost_eur_estimated']:.5f} EUR > 0.015 EUR"
    )

    # Classification coherente entre runs (determinismo a T=0.1)
    assert first["qualification"]["classification"] == second["qualification"]["classification"]
    assert first["fallback_used"] is False
    assert second["fallback_used"] is False
