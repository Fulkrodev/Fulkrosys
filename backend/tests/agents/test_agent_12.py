"""Tests Agente 12 - Coach Cliente EVALUADOR (Sesion 9 Paso 2.8).

Scope EVALUADOR (no generador). M9 coaching determinista es la unica
fuente de preguntas. A12 scorea las respuestas del cliente a esas
preguntas con rubrica L0-L5.

Tests clave:
- Schema strict (7 claves + enums madurez/gaps/urgencia).
- Coherencia madurez <-> dimension_scores.
- Anti-hallucination: template ideal NO inventa sistemas/productos
  que no esten en la respuesta cliente.
- Fallback keyword scoring.

LLM tests se saltan si ANTHROPIC_API_KEY no esta configurado.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_12_coach_cliente import (
    Agent12CoachClienteEvaluador,
    CoachClienteAgent,
    _DIMENSION_KEYS,
    _ENS_CATEGORIES,
    _GAP_TIPOS,
    _MATURITY_LEVELS,
    _REQUIRED_KEYS,
    _ROLES,
    _SECTORS,
    _URGENCIAS,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


# Pregunta y respuesta ejemplo (L5 caso ideal)
PREGUNTA_MFA = {
    "id": "Q_CISO_042",
    "role": "CISO",
    "texto": "Como garantiza que el MFA esta activado en TODAS las aplicaciones criticas del alcance?",
    "criterio_L5_ideal": "Menciona sistemas + tecnologia + politica + evidencia + frecuencia + responsable",
}
RESPUESTA_CISO_L5 = {
    "texto": (
        "MFA obligatorio en Azure AD via Conditional Access para los 47 "
        "usuarios con acceso a HCE + sede electronica + portal pacientes. "
        "Politica MFA-2024-v3 aprobada Comite Seguridad 15 enero 2026, "
        "revisada trimestralmente (ultima 10 abril con 100% cumplimiento "
        "log Azure AD). Responsable RSEG Ana Martin. Cumple op.acc.5 ENS "
        "y RGPD art. 32."
    ),
    "rol_cliente": "CISO",
}
RESPUESTA_L2_GENERICA = {
    "texto": "Tenemos MFA.",
    "rol_cliente": "CISO",
}

DATAFORMA_CTX = {
    "company_name": "DataForma S.L.",
    "sector": "sanidad",
    "ens_category": "MEDIA",
}


def _valid_evaluation(
    *,
    score: int = 87,
    madurez: str = "L5",
    completitud: int = 90,
    exactitud: int = 90,
    evidencia: int = 80,
    template_words: int = 150,
) -> dict:
    template = (
        "Un CISO senior ampliaria esta respuesta ya solida citando la "
        "version exacta del log Azure AD y ofreciendo enseniarlo en "
        "pantalla durante la entrevista del auditor. Explicaria el "
        "procedimiento de excepcion MFA cuando un usuario pierde el "
        "segundo factor. Mencionaria la integracion con el SIEM "
        "corporativo para alertas anomalas. Finalmente, aportaria el "
        "acta de la reunion del Comite de Seguridad donde se aprobo la "
        "politica MFA. El auditor ENAC valoraria positivamente tanto el "
        "procedimiento formal documentado como la metrica concreta de "
        "cumplimiento (100% en el ultimo periodo)."
    )
    # Ajustar a template_words palabras aproximadamente
    words = template.split()
    if len(words) < template_words:
        template += " " + " ".join(["texto"] * (template_words - len(words)))
    return {
        "score_global": score,
        "madurez_respuesta": madurez,
        "dimension_scores": {
            "completitud": completitud,
            "exactitud": exactitud,
            "evidencia_referenciada": evidencia,
        },
        "gaps_detectados": [
            {
                "tipo": "falta_evidencia",
                "descripcion": "Responde bien pero no aporta URL del log Azure AD para verificar.",
            },
        ],
        "respuesta_ideal_template": template,
        "next_actions_cliente": [
            {
                "accion": "Preparar captura Azure AD Sign-in Log",
                "evidencia_a_aportar": "Screenshot + URL",
                "urgencia": "antes_audit",
            },
        ],
        "feedback_marcos": "Respuesta casi perfecta L5. Solo faltan capturas log.",
    }


def _mock_llm_response(evaluation: dict, *, tokens_in: int = 2500, tokens_out: int = 1500) -> dict:
    return {
        "agent_id": 12,
        "agent_name": "Coach Cliente Evaluador",
        "response": "{...}",
        "parsed": evaluation,
        "model": "claude-sonnet-4-6",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 15000,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Alias retrocompat + enums
# =======================================================================


def test_agent_12_alias_backcompat():
    assert CoachClienteAgent is Agent12CoachClienteEvaluador


def test_agent_12_enums_match_spec():
    assert _MATURITY_LEVELS == {"L0", "L1", "L2", "L3", "L4", "L5"}
    assert _SECTORS == {"sanidad", "aapp", "fintech", "otro"}
    assert _ENS_CATEGORIES == {"BASICA", "MEDIA", "ALTA"}
    assert _ROLES == {"CISO", "RSEG", "CTO", "direccion", "tech"}
    assert _GAP_TIPOS == {
        "falta_evidencia", "respuesta_vaga", "dato_inconsistente",
        "alcance_no_claro", "cita_normativa_incorrecta",
    }
    assert _URGENCIAS == {"inmediata", "1_semana", "antes_audit"}
    assert len(_REQUIRED_KEYS) == 7
    assert len(_DIMENSION_KEYS) == 3


# =======================================================================
# 2) Input validation
# =======================================================================


async def test_agent_12_missing_pregunta_field_raises(db):
    agent = Agent12CoachClienteEvaluador()
    bad_pregunta = {"id": "Q1"}  # falta role y texto
    with pytest.raises(ValueError, match="pregunta_coaching falta"):
        await agent.evaluate_client_response(
            db,
            pregunta_coaching=bad_pregunta,
            respuesta_cliente=RESPUESTA_CISO_L5,
            client_context=DATAFORMA_CTX,
        )


async def test_agent_12_invalid_sector_raises(db):
    agent = Agent12CoachClienteEvaluador()
    ctx = {**DATAFORMA_CTX, "sector": "inventado"}
    with pytest.raises(ValueError, match="sector invalido"):
        await agent.evaluate_client_response(
            db,
            pregunta_coaching=PREGUNTA_MFA,
            respuesta_cliente=RESPUESTA_CISO_L5,
            client_context=ctx,
        )


# =======================================================================
# 3) Mock success L5 rich
# =======================================================================


async def test_agent_12_rich_response_scores_L5(db):
    agent = Agent12CoachClienteEvaluador()
    good = _mock_llm_response(_valid_evaluation())
    with patch.object(
        Agent12CoachClienteEvaluador, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.evaluate_client_response(
            db,
            pregunta_coaching=PREGUNTA_MFA,
            respuesta_cliente=RESPUESTA_CISO_L5,
            client_context=DATAFORMA_CTX,
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    e = result["evaluation"]
    assert e["madurez_respuesta"] == "L5"
    assert e["score_global"] >= 80


# =======================================================================
# 4) Coherencia madurez <-> scores
# =======================================================================


def test_agent_12_coherencia_madurez_rejects_L5_with_low_scores():
    """3 scores <30 no pueden ser L4 o L5."""
    agent = Agent12CoachClienteEvaluador()
    inconsistent = _valid_evaluation(
        madurez="L5", completitud=20, exactitud=25, evidencia=15,
    )
    errs = agent._validate_schema(inconsistent, RESPUESTA_L2_GENERICA)
    assert any("incoherente" in e for e in errs)


def test_agent_12_coherencia_madurez_rejects_L0_with_high_scores():
    """3 scores >=85 no pueden ser L0 o L1."""
    agent = Agent12CoachClienteEvaluador()
    inconsistent = _valid_evaluation(
        madurez="L0", completitud=90, exactitud=90, evidencia=88,
    )
    errs = agent._validate_schema(inconsistent, RESPUESTA_CISO_L5)
    assert any("incoherente" in e for e in errs)


def test_agent_12_coherencia_madurez_allows_L3_mixed_scores():
    """Scores mezclados (algunos bajos algunos altos) permite L3 sin error."""
    agent = Agent12CoachClienteEvaluador()
    ok = _valid_evaluation(
        madurez="L3", completitud=60, exactitud=50, evidencia=40,
    )
    errs = agent._validate_schema(ok, RESPUESTA_CISO_L5)
    assert not any("incoherente" in e for e in errs)


# =======================================================================
# 5) Schema strict validation
# =======================================================================


@pytest.mark.parametrize(
    "mutator,expected_substring",
    [
        (lambda e: e.__setitem__("score_global", 150), "score_global"),
        (lambda e: e.__setitem__("madurez_respuesta", "L9"), "madurez_respuesta"),
        (lambda e: e["dimension_scores"].__setitem__("completitud", 150), "completitud"),
        (
            lambda e: e["gaps_detectados"].append(
                {"tipo": "inexistente", "descripcion": "x"}
            ),
            "tipo invalido",
        ),
        (
            lambda e: e["next_actions_cliente"][0].__setitem__("urgencia", "nunca"),
            "urgencia invalida",
        ),
        (lambda e: e.__setitem__("respuesta_ideal_template", "corto"), "muy corta"),
    ],
)
def test_agent_12_schema_strict_validation(mutator, expected_substring):
    agent = Agent12CoachClienteEvaluador()
    evaluation = _valid_evaluation()
    mutator(evaluation)
    errs = agent._validate_schema(evaluation, RESPUESTA_CISO_L5)
    assert any(expected_substring in e for e in errs), errs


# =======================================================================
# 6) Anti-hallucination: template NO inventa sistemas
# =======================================================================


def test_agent_12_rejects_invented_system_in_template():
    """Si template menciona 'Splunk' pero cliente no, rechazo."""
    agent = Agent12CoachClienteEvaluador()
    bad = _valid_evaluation()
    bad["respuesta_ideal_template"] += (
        " Adicionalmente, Splunk Enterprise correlaciona eventos 24x7."
    )
    errs = agent._validate_schema(bad, RESPUESTA_CISO_L5)
    assert any("hallucinated_system" in e for e in errs)
    assert any("splunk" in e.lower() for e in errs)


def test_agent_12_allows_system_mentioned_by_client():
    """Si cliente dice 'Azure AD', template puede mencionarlo."""
    agent = Agent12CoachClienteEvaluador()
    ok = _valid_evaluation()
    # El template valido YA menciona Azure AD; el cliente tambien
    # (RESPUESTA_CISO_L5 tiene 'Azure AD') -> OK
    errs = agent._validate_schema(ok, RESPUESTA_CISO_L5)
    assert not any("hallucinated_system" in e for e in errs)


def test_agent_12_rejects_invented_veeam_backup():
    agent = Agent12CoachClienteEvaluador()
    bad = _valid_evaluation()
    bad["respuesta_ideal_template"] += (
        " Los backups diarios se gestionan con Veeam Backup & Replication."
    )
    errs = agent._validate_schema(bad, RESPUESTA_CISO_L5)
    assert any("hallucinated_system" in e for e in errs)


# =======================================================================
# 7) Fallback keyword scoring
# =======================================================================


async def test_agent_12_fallback_on_invalid_json(db):
    agent = Agent12CoachClienteEvaluador()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 500, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    with patch.object(
        Agent12CoachClienteEvaluador, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.evaluate_client_response(
            db,
            pregunta_coaching=PREGUNTA_MFA,
            respuesta_cliente=RESPUESTA_L2_GENERICA,
            client_context=DATAFORMA_CTX,
        )

    assert result["fallback_used"] is True
    e = result["evaluation"]
    # Respuesta corta "Tenemos MFA" -> score bajo + madurez L1-L2
    assert e["madurez_respuesta"] in {"L0", "L1", "L2"}
    assert e["score_global"] < 50
    # Fallback siempre detecta al menos 1 gap
    assert len(e["gaps_detectados"]) >= 1


async def test_agent_12_fallback_rich_response_higher_score(db):
    """Fallback con respuesta rica da score mayor que respuesta pobre."""
    agent = Agent12CoachClienteEvaluador()
    bad = {
        "response": "no json", "parsed": None,
        "tokens_input": 500, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    with patch.object(
        Agent12CoachClienteEvaluador, "invoke", new=AsyncMock(return_value=bad)
    ):
        rich = await agent.evaluate_client_response(
            db,
            pregunta_coaching=PREGUNTA_MFA,
            respuesta_cliente=RESPUESTA_CISO_L5,
            client_context=DATAFORMA_CTX,
        )
        poor = await agent.evaluate_client_response(
            db,
            pregunta_coaching=PREGUNTA_MFA,
            respuesta_cliente=RESPUESTA_L2_GENERICA,
            client_context=DATAFORMA_CTX,
        )

    assert rich["evaluation"]["score_global"] > poor["evaluation"]["score_global"]


# =======================================================================
# 8) LLM real - respuesta L5 rica sanidad
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_12_respuesta_L5_sanidad_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent12CoachClienteEvaluador()
    result = await agent.evaluate_client_response(
        db,
        pregunta_coaching=PREGUNTA_MFA,
        respuesta_cliente=RESPUESTA_CISO_L5,
        client_context=DATAFORMA_CTX,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    e = result["evaluation"]
    # Respuesta rica -> esperamos L4 o L5
    assert e["madurez_respuesta"] in {"L4", "L5"}
    assert e["score_global"] >= 70
    # dimension_scores coherentes con la madurez alta
    assert e["dimension_scores"]["completitud"] >= 70


# =======================================================================
# 9) LLM real - respuesta L1 aapp
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_12_respuesta_L1_aapp_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent12CoachClienteEvaluador()
    pregunta = {
        "id": "Q_DIR_007",
        "role": "direccion",
        "texto": "Esta dado de alta en FACe como punto de entrada de facturas electronicas?",
        "criterio_L5_ideal": "Fecha alta + codigo DIR3 + procedimiento facturacion",
    }
    respuesta = {
        "texto": "Creo que si, lo gestiona el departamento de informatica.",
        "rol_cliente": "director",
    }
    ctx = {
        "company_name": "Ayuntamiento de Villanueva",
        "sector": "aapp",
        "ens_category": "BASICA",
    }
    result = await agent.evaluate_client_response(
        db,
        pregunta_coaching=pregunta,
        respuesta_cliente=respuesta,
        client_context=ctx,
    )

    assert result["fallback_used"] is False, (
        f"Fallback; errores={result['schema_errors'][:3]}"
    )
    e = result["evaluation"]
    # "Creo que si" -> respuesta L1-L2 max
    assert e["madurez_respuesta"] in {"L0", "L1", "L2"}
    assert e["score_global"] < 50
    # Debe detectar al menos 1 gap
    assert len(e["gaps_detectados"]) >= 1


# =======================================================================
# 10) LLM real - prompt caching reduce coste batch
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(400)
async def test_agent_12_prompt_caching_reduces_cost(db):
    _skip_if_no_api_key()
    agent = Agent12CoachClienteEvaluador()

    first = await agent.evaluate_client_response(
        db,
        pregunta_coaching=PREGUNTA_MFA,
        respuesta_cliente=RESPUESTA_CISO_L5,
        client_context=DATAFORMA_CTX,
    )
    second = await agent.evaluate_client_response(
        db,
        pregunta_coaching=PREGUNTA_MFA,
        respuesta_cliente=RESPUESTA_L2_GENERICA,
        client_context=DATAFORMA_CTX,
    )

    assert first["cache_read_input_tokens"] > 0 or second["cache_read_input_tokens"] > 0
    assert second["cache_read_input_tokens"] > 0
    # A12 output medio ~1500 tokens -> ~0.02 EUR base; con cache ~0.025 max
    assert second["cost_eur_estimated"] < 0.030, (
        f"Run 2 coste {second['cost_eur_estimated']:.5f} EUR > 0.030 EUR"
    )
