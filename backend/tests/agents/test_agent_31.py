"""Tests Agente 31 - Enriquecedor DdA no_aplica (Sesion 9 Paso 2.7).

PRIMER agente nuevo desde cero (id 31). Tests clave:
- Schema strict: justificacion 60-200 palabras + elementos_contexto
  no vacio + confianza [0,1].
- Anti-hallucination: validator detecta menciones a empresas/
  productos (AWS, Azure, Google, SAP, Oracle, etc.) que NO estan en
  client_context + system_context_from_m22.
- Fallback al template estatico M3 cuando LLM falla.
- Caching critico: 15-30 invocaciones por proyecto reutilizan system.

LLM tests se saltan si ANTHROPIC_API_KEY no esta configurado.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_31_enriquecedor_dda import (
    Agent31EnriquecedorDdA,
    _BASE_REASONS,
    _ENS_CATEGORIES,
    _HOSTING_MODELS,
    _MAX_WORDS,
    _MIN_WORDS,
    _REQUIRED_KEYS,
    _SECTORS,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


DATAFORMA_CTX = {
    "company_name": "DataForma S.L.",
    "sector": "sanidad",
    "ens_category": "MEDIA",
    "is_aapp": False,
    "alcance_texto": "HCE + sede electronica + portal pacientes",
}
DATAFORMA_M22 = {
    "hosting_model": "cloud_saas",
    "cloud_providers": ["AWS EU-West"],
    "physical_offices": [
        {"address": "Calle Alcala 123, Madrid", "role": "admin_only"},
    ],
    "frameworks_heredados": ["ISO 27001", "SOC 2 Type II"],
    "outsourced_services": ["hosting"],
}


def _valid_enrichment(
    *,
    words: int = 90,
    cloud_provider: str = "AWS EU-West",
    framework: str = "ISO 27001",
) -> dict:
    """EnrichmentResult valido citando datos del input."""
    # Construir texto de ~90 palabras que cite el provider y framework
    base = (
        f"DataForma S.L. opera el sistema bajo un modelo cloud SaaS al 100%, "
        f"con la infraestructura productiva alojada en los centros de datos "
        f"de {cloud_provider}. Las medidas fisicas de control de acceso en "
        f"dichos centros estan cubiertas por el proveedor, cuyas certificaciones "
        f"vigentes {framework} acreditan el cumplimiento de los controles. "
        f"Las oficinas de Calle Alcala 123 en Madrid tienen rol unicamente "
        f"administrativo y no albergan infraestructura TIC del alcance HCE "
        f"+ sede electronica + portal pacientes. La medida mp.if.7 no resulta "
        f"de aplicacion conforme al criterio de la CCN-STIC 803 y la CCN-STIC "
        f"823 sobre tercerizacion y delimitacion del alcance certificado."
    )
    # Ajuste a ~words palabras si necesario
    current_words = base.split()
    if len(current_words) < words:
        base += " " + " ".join(["texto"] * (words - len(current_words)))
    elif len(current_words) > words:
        base = " ".join(current_words[:words])
    return {
        "justificacion_enriquecida": base,
        "ccn_stic_referenciada": "CCN-STIC 803",
        "elementos_contexto_usados": [
            "company_name", "cloud_providers", "physical_offices",
            "frameworks_heredados", "alcance_texto",
        ],
        "confianza": 0.9,
    }


def _mock_llm_response(enrichment: dict, *, tokens_in: int = 1000, tokens_out: int = 500) -> dict:
    return {
        "agent_id": 31,
        "agent_name": "Enriquecedor DdA no_aplica",
        "response": "{...}",
        "parsed": enrichment,
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
# 1) Registry + enums
# =======================================================================


def test_agent_31_registered_as_new_id_31():
    from backend.app.agents.registry import AGENT_REGISTRY
    assert 31 in AGENT_REGISTRY
    info = AGENT_REGISTRY[31]
    assert info["status"] == "activo"
    assert info["model"] == "sonnet-4.6"
    assert info["motor"] == "m03"


def test_agent_31_enums_match_spec():
    assert _BASE_REASONS == {
        "scope_exclusion", "cloud_only", "outsourced",
        "not_applicable_sector", "compensated_by_other",
    }
    assert _ENS_CATEGORIES == {"BASICA", "MEDIA", "ALTA"}
    assert _SECTORS == {"sanidad", "aapp", "fintech", "otro"}
    assert _HOSTING_MODELS == {
        "cloud_saas", "cloud_iaas", "on_premise", "hybrid",
    }
    assert len(_REQUIRED_KEYS) == 4
    assert _MIN_WORDS == 60
    assert _MAX_WORDS == 200


# =======================================================================
# 2) Input validation
# =======================================================================


async def test_agent_31_invalid_base_reason_raises(db):
    agent = Agent31EnriquecedorDdA()
    with pytest.raises(ValueError, match="base_reason invalido"):
        await agent.enrich_no_aplica_justification(
            db,
            measure_id="mp.if.7",
            measure_name="Registro entrada/salida",
            measure_family="mp.if",
            base_reason="magia",
            client_context=DATAFORMA_CTX,
            system_context_from_m22=DATAFORMA_M22,
        )


async def test_agent_31_invalid_sector_raises(db):
    agent = Agent31EnriquecedorDdA()
    ctx = {**DATAFORMA_CTX, "sector": "magia"}
    with pytest.raises(ValueError, match="sector invalido"):
        await agent.enrich_no_aplica_justification(
            db,
            measure_id="mp.if.7",
            measure_name="Registro entrada/salida",
            measure_family="mp.if",
            base_reason="cloud_only",
            client_context=ctx,
            system_context_from_m22=DATAFORMA_M22,
        )


# =======================================================================
# 3) Mock success path
# =======================================================================


async def test_agent_31_complete_mock_success(db):
    agent = Agent31EnriquecedorDdA()
    good = _mock_llm_response(_valid_enrichment())
    with patch.object(
        Agent31EnriquecedorDdA, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.enrich_no_aplica_justification(
            db,
            measure_id="mp.if.7",
            measure_name="Registro entrada/salida",
            measure_family="mp.if",
            base_reason="cloud_only",
            client_context=DATAFORMA_CTX,
            system_context_from_m22=DATAFORMA_M22,
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    e = result["enrichment"]
    assert "AWS EU-West" in e["justificacion_enriquecida"]
    assert "ISO 27001" in e["justificacion_enriquecida"]


# =======================================================================
# 4) Schema strict validation
# =======================================================================


def test_agent_31_schema_rejects_short_justification():
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    bad["justificacion_enriquecida"] = "Corto."
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("muy corta" in e for e in errs)


def test_agent_31_schema_rejects_long_justification():
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    bad["justificacion_enriquecida"] = " ".join(["palabra"] * 300)
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("muy larga" in e for e in errs)


def test_agent_31_schema_rejects_empty_elementos():
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    bad["elementos_contexto_usados"] = []
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("elementos_contexto_usados vacio" in e for e in errs)


def test_agent_31_schema_rejects_confianza_out_of_range():
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    bad["confianza"] = 1.5
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("confianza fuera" in e for e in errs)


# =======================================================================
# 5) Anti-hallucination CRITICO - empresas inventadas
# =======================================================================


def test_agent_31_rejects_invented_cloud_provider():
    """LLM menciona Google Cloud pero solo AWS esta en el input -> rechazo."""
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    # Inyectar mencion a Google Cloud (no esta en DATAFORMA_M22)
    bad["justificacion_enriquecida"] += (
        " Adicionalmente se considera el uso de Google Cloud como fallback."
    )
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("hallucinated_entity" in e for e in errs)
    assert any("google cloud" in e.lower() for e in errs)


def test_agent_31_rejects_invented_azure():
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    bad["justificacion_enriquecida"] += (
        " Los backups se replican en Azure Spain para alta disponibilidad."
    )
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("hallucinated_entity" in e for e in errs)


def test_agent_31_allows_aws_when_in_whitelist():
    """AWS EU-West SI esta en input -> validator lo permite."""
    agent = Agent31EnriquecedorDdA()
    ok = _valid_enrichment()
    # El texto valido YA contiene AWS EU-West -> no debe dar error
    errs = agent._validate_schema(ok, DATAFORMA_CTX, DATAFORMA_M22)
    assert not any("hallucinated_entity" in e for e in errs)


def test_agent_31_rejects_invented_third_party_tool():
    """LLM menciona Salesforce pero no esta en input -> rechazo."""
    agent = Agent31EnriquecedorDdA()
    bad = _valid_enrichment()
    bad["justificacion_enriquecida"] += (
        " La gestion comercial se apoya en Salesforce fuera del alcance."
    )
    errs = agent._validate_schema(bad, DATAFORMA_CTX, DATAFORMA_M22)
    assert any("hallucinated_entity" in e for e in errs)
    assert any("salesforce" in e.lower() for e in errs)


# =======================================================================
# 6) Fallback al template estatico M3
# =======================================================================


async def test_agent_31_fallback_on_invalid_json(db):
    agent = Agent31EnriquecedorDdA()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 100, "tokens_output": 10, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    with patch.object(
        Agent31EnriquecedorDdA, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.enrich_no_aplica_justification(
            db,
            measure_id="mp.if.7",
            measure_name="Registro entrada/salida",
            measure_family="mp.if",
            base_reason="cloud_only",
            client_context=DATAFORMA_CTX,
            system_context_from_m22=DATAFORMA_M22,
        )

    assert result["fallback_used"] is True
    e = result["enrichment"]
    # Fallback cumple el minimo 60 palabras
    assert len(e["justificacion_enriquecida"].split()) >= 60
    # Usa el measure_id y el codigo real
    assert "mp.if.7" in e["justificacion_enriquecida"]
    assert e["ccn_stic_referenciada"] == "CCN-STIC 803"
    assert e["confianza"] == 0.3  # confianza baja por fallback


# =======================================================================
# 7) Batch helper
# =======================================================================


async def test_agent_31_enrich_batch_invokes_once_per_measure(db):
    agent = Agent31EnriquecedorDdA()
    measures = [
        {"measure_id": "mp.if.7", "measure_name": "Registro entrada/salida", "measure_family": "mp.if", "base_reason": "cloud_only"},
        {"measure_id": "mp.if.8", "measure_name": "Proteccion desastres", "measure_family": "mp.if", "base_reason": "outsourced"},
        {"measure_id": "mp.per.4", "measure_name": "Personal confianza", "measure_family": "mp.per", "base_reason": "not_applicable_sector"},
    ]
    good = _mock_llm_response(_valid_enrichment())
    with patch.object(
        Agent31EnriquecedorDdA, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        results = await agent.enrich_batch(
            db,
            measures=measures,
            client_context=DATAFORMA_CTX,
            system_context_from_m22=DATAFORMA_M22,
        )

    assert len(results) == 3
    assert invoke_mock.call_count == 3
    for r in results:
        assert r["fallback_used"] is False


# =======================================================================
# 8) LLM real - mp.if.7 DataForma sanidad cloud_only
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(180)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_31_cloud_only_sanidad_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent31EnriquecedorDdA()
    result = await agent.enrich_no_aplica_justification(
        db,
        measure_id="mp.if.7",
        measure_name="Registro de entrada y salida",
        measure_family="mp.if",
        base_reason="cloud_only",
        client_context=DATAFORMA_CTX,
        system_context_from_m22=DATAFORMA_M22,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    e = result["enrichment"]
    # Justificacion con longitud adecuada
    word_count = len(e["justificacion_enriquecida"].split())
    assert 60 <= word_count <= 200
    # Cita el provider real (AWS EU-West)
    text = e["justificacion_enriquecida"]
    assert "AWS" in text, f"No cita AWS en el texto: {text[:200]}"
    # Al menos una cita CCN-STIC 800-899
    import re
    assert re.search(r"\bCCN-?STIC\s*8\d{2}\b", text), (
        f"No cita CCN-STIC 800-899: {text[:300]}"
    )


# =======================================================================
# 9) LLM real - AAPP scope_exclusion
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(180)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_31_aapp_scope_exclusion_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent31EnriquecedorDdA()
    result = await agent.enrich_no_aplica_justification(
        db,
        measure_id="op.exp.9",
        measure_name="Registro de actividad",
        measure_family="op.exp",
        base_reason="not_applicable_sector",
        client_context={
            "company_name": "Ayuntamiento de Villanueva",
            "sector": "aapp",
            "ens_category": "BASICA",
            "is_aapp": True,
            "alcance_texto": "Portal ciudadano + padron municipal",
        },
        system_context_from_m22={
            "hosting_model": "on_premise",
            "cloud_providers": [],
            "physical_offices": [
                {"address": "Plaza Mayor 1, Villanueva", "role": "main_office"},
            ],
            "frameworks_heredados": [],
            "outsourced_services": ["soporte_tecnico_externo"],
        },
    )

    assert result["fallback_used"] is False, (
        f"Fallback; errores={result['schema_errors'][:3]}"
    )
    e = result["enrichment"]
    assert 60 <= len(e["justificacion_enriquecida"].split()) <= 200
    # Cita Ayuntamiento o Villanueva
    text_low = e["justificacion_enriquecida"].lower()
    assert "villanueva" in text_low or "ayuntamiento" in text_low


# =======================================================================
# 10) LLM real - prompt caching CRITICO (15+ invocaciones/proyecto)
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
async def test_agent_31_prompt_caching_reduces_cost_batch(db):
    """3 invocaciones consecutivas: medida 2 y 3 deben leer cache."""
    _skip_if_no_api_key()
    agent = Agent31EnriquecedorDdA()
    medidas = [
        ("mp.if.7", "Registro entrada/salida", "cloud_only"),
        ("mp.if.8", "Proteccion desastres", "cloud_only"),
        ("op.pl.2", "Arquitectura seguridad", "cloud_only"),
    ]
    results = []
    for mid, mname, reason in medidas:
        r = await agent.enrich_no_aplica_justification(
            db,
            measure_id=mid,
            measure_name=mname,
            measure_family=mid.rsplit(".", 1)[0],
            base_reason=reason,
            client_context=DATAFORMA_CTX,
            system_context_from_m22=DATAFORMA_M22,
        )
        results.append(r)

    # Al menos una invocacion escribe cache y la ultima lee
    total_cache_read = sum(r["cache_read_input_tokens"] for r in results)
    assert total_cache_read > 0, (
        f"Ningun run leyo cache. "
        f"reads={[r['cache_read_input_tokens'] for r in results]}"
    )
    # La ultima invocacion debe leer cache
    assert results[-1]["cache_read_input_tokens"] > 0

    # Coste medida 2 o 3 debe ser significativamente menor que medida 1
    # (por cache hit). Output A31 ~500 tokens -> ~0.007 EUR cacheado.
    # Tope holgado 0.015 EUR para medida 3.
    assert results[-1]["cost_eur_estimated"] < 0.015, (
        f"Ultima medida coste {results[-1]['cost_eur_estimated']:.5f} EUR "
        "demasiado alto para caching activo."
    )
