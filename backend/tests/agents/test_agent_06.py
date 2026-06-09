"""Tests Agente 6 - Analista Contratos Proveedor (Sesion 9 Paso 2.4).

Patron A17/A18/A20:
- Tests deterministas (mock LLM con AsyncMock): fallback vacio, regex
  fallback, contrato completo mockeado, schema strict validation.
- Tests @pytest.mark.llm con llamada real Sonnet 4.6 sobre 2 ejemplos
  sectoriales (AWS hosting sanidad, Salesforce fintech).
- Test caching (@llm): crucial aqui porque caso de uso es 10+
  proveedores del mismo cliente en cascada.

Los tests LLM se saltan automaticamente si ANTHROPIC_API_KEY no esta
configurado (.env via python-dotenv).
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_06_contratos import (
    Agent06AnalistaContratos,
    AnalistaContratosAgent,
    _ACTIONS,
    _BASE_CLAUSE_IDS,
    _CLAUSE_QUALITY,
    _CLIENT_SECTORS,
    _COMPLIANCE_LEVELS,
    _ENS_CATEGORIES,
    _ENS_ALTA_CLAUSE_IDS,
    _ENS_MEDIA_PLUS_CLAUSE_IDS,
    _PROVIDER_ROLES,
    _REQUIRED_KEYS,
    _SEVERITIES,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


AWS_CONTRACT_COMPLETE = """
CONTRATO DE SERVICIOS CLOUD COMPUTING ENTRE DATAFORMA S.L. Y AMAZON WEB SERVICES EMEA SARL

Clausula 1. Objeto: Prestacion de servicios de infraestructura cloud.

Clausula 2. Acuerdo de Encargado del Tratamiento (RGPD art. 28). AWS actuara
como encargado del tratamiento conforme al art. 28 RGPD bajo instrucciones
documentadas del responsable, confidencialidad extensible al personal,
subencargados con autorizacion previa, devolucion/destruccion al terminar.

Clausula 3. Ubicacion datos: Los datos se almacenaran exclusivamente en la
region eu-west-1 (Irlanda), Union Europea.

Clausula 4. Confidencialidad: AWS y su personal estan obligados a
confidencialidad indefinida.

Clausula 5. Medidas de seguridad de la informacion ENS: AWS implementara
las medidas del RD 311/2022 Anexo II proporcionales a categoria MEDIA.

Clausula 6. Notificacion de incidentes: AWS notificara al cliente cualquier
violacion de seguridad en un plazo maximo de 72 horas.

Clausula 7. Derecho de auditoria: El cliente podra auditar los controles
del proveedor con preaviso de 30 dias.

Clausula 8. Subcontratacion: No se subcontratara sin autorizacion escrita
previa del responsable.

Clausula 9. Devolucion datos: AWS devolvera o destruira los datos a la
terminacion del contrato.

Clausula 10. Duracion: 36 meses prorrogables.
"""


AWS_CONTRACT_WEAK = """
ACUERDO DE SERVICIOS CON UN PROVEEDOR DE HOSTING

1. El proveedor prestara servicios de hosting web.
2. Precio: 200 EUR mensuales.
3. Duracion: 12 meses.
4. El proveedor implementara medidas de seguridad.
"""


def _valid_analysis_for_media(provider_name: str = "AWS") -> dict:
    """Analysis valido cubriendo todas las clausulas base + MEDIA."""
    clauses = []
    for cid in _BASE_CLAUSE_IDS:
        clauses.append({
            "clause_id": cid,
            "clause_name": cid.replace("_", " ").title(),
            "present": True,
            "quality": "completo",
            "evidence_excerpt": f"Clausula {cid} presente en contrato",
            "gap_description": "",
        })
    for cid in _ENS_MEDIA_PLUS_CLAUSE_IDS:
        clauses.append({
            "clause_id": cid,
            "clause_name": cid.replace("_", " ").title(),
            "present": True,
            "quality": "completo",
            "evidence_excerpt": f"Clausula {cid} presente",
            "gap_description": "",
        })
    return {
        "compliance_score": 85,
        "compliance_level": "conforme",
        "mandatory_clauses_check": clauses,
        "sector_specific_gaps": [],
        "addendum_text": f"ADDENDUM menor al contrato con {provider_name}...",
        "recommendation": {
            "action": "firmar_adenda",
            "urgency": "1_trimestre",
            "rationale": "Contrato casi completo; adenda menor.",
        },
        "red_flags": [],
    }


def _valid_llm_response(analysis: dict, *, tokens_in: int = 2500, tokens_out: int = 1800) -> dict:
    return {
        "agent_id": 6,
        "agent_name": "Analista de Contratos",
        "response": "{...}",
        "parsed": analysis,
        "model": "claude-sonnet-4-6",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 8000,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Alias retrocompat + enums expuestos
# =======================================================================


def test_agent_06_alias_backcompat():
    assert AnalistaContratosAgent is Agent06AnalistaContratos


def test_agent_06_enums_match_spec():
    assert _COMPLIANCE_LEVELS == {"conforme", "parcial", "no_conforme", "critico"}
    assert _CLAUSE_QUALITY == {"completo", "incompleto", "ausente"}
    assert _SEVERITIES == {"critico", "alto", "medio", "bajo"}
    assert "firmar_adenda" in _ACTIONS
    assert "renegociar_contrato" in _ACTIONS
    assert _ENS_CATEGORIES == {"BASICA", "MEDIA", "ALTA"}
    assert "sanidad" in _CLIENT_SECTORS
    assert "fintech" in _CLIENT_SECTORS
    assert "hosting" in _PROVIDER_ROLES
    assert len(_REQUIRED_KEYS) == 7
    # Base + MEDIA + ALTA suman 13 clausulas totales
    total = len(_BASE_CLAUSE_IDS) + len(_ENS_MEDIA_PLUS_CLAUSE_IDS) + len(_ENS_ALTA_CLAUSE_IDS)
    assert total == 13


# =======================================================================
# 2) Fallback contrato vacio - no gasta LLM
# =======================================================================


async def test_agent_06_empty_contract_fallback_no_llm_call(db):
    agent = Agent06AnalistaContratos()
    with patch.object(
        Agent06AnalistaContratos, "invoke", new=AsyncMock()
    ) as invoke_mock:
        result = await agent.analyze_provider_contract(
            db,
            contract_text="",
            provider_name="Unknown Provider",
            provider_role="hosting",
            criticality="alta",
            data_processed="datos_clientes",
            ens_category="MEDIA",
            client_sector="sanidad",
        )

    # Fallback directo sin llamar al LLM
    invoke_mock.assert_not_called()
    assert result["fallback_used"] is True
    assert result["analysis"]["compliance_score"] == 0
    assert result["analysis"]["compliance_level"] == "critico"
    assert result["analysis"]["recommendation"]["action"] == "renegociar_contrato"


# =======================================================================
# 3) Contrato completo AWS puntua conforme (mock LLM)
# =======================================================================


async def test_agent_06_complete_aws_contract_mock_scores_conforme(db):
    agent = Agent06AnalistaContratos()
    good = _valid_llm_response(_valid_analysis_for_media("AWS"))
    with patch.object(
        Agent06AnalistaContratos, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        result = await agent.analyze_provider_contract(
            db,
            contract_text=AWS_CONTRACT_COMPLETE,
            provider_name="AWS EMEA SARL",
            provider_role="hosting",
            criticality="alta",
            data_processed="datos_clientes",
            ens_category="MEDIA",
            client_sector="otro",
        )

    assert invoke_mock.call_count == 1
    assert result["fallback_used"] is False
    assert result["schema_valid"] is True
    assert result["analysis"]["compliance_level"] == "conforme"
    assert result["analysis"]["compliance_score"] >= 70


# =======================================================================
# 4) Contrato incompleto cae a regex fallback tras retry
# =======================================================================


async def test_agent_06_incomplete_contract_regex_fallback(db):
    agent = Agent06AnalistaContratos()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 500, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-sonnet-4-6",
    }
    with patch.object(
        Agent06AnalistaContratos, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.analyze_provider_contract(
            db,
            contract_text=AWS_CONTRACT_WEAK,
            provider_name="Weak Provider",
            provider_role="hosting",
            criticality="media",
            data_processed="datos_clientes",
            ens_category="MEDIA",
            client_sector="otro",
        )

    assert result["fallback_used"] is True
    # Regex detecta "duracion" pero marca ausentes: art. 28, confidencialidad, etc.
    analysis = result["analysis"]
    assert analysis["compliance_level"] in {"critico", "no_conforme", "parcial"}
    clauses_by_id = {c["clause_id"]: c for c in analysis["mandatory_clauses_check"]}
    # art_28_dpa NO aparece en el contrato WEAK -> present=False
    assert clauses_by_id["art_28_dpa"]["present"] is False
    assert clauses_by_id["duracion_contrato"]["present"] is True
    # Recomendacion renegociar
    assert analysis["recommendation"]["action"] == "renegociar_contrato"


# =======================================================================
# 5) Schema strict validation
# =======================================================================


@pytest.mark.parametrize(
    "corruption,expected_error_substring",
    [
        ({"compliance_score": 150}, "compliance_score"),
        ({"compliance_level": "muy_bien"}, "compliance_level"),
        ({"mandatory_clauses_check": []}, "mandatory_clauses_check"),
        (
            {"recommendation": {"action": "bogus", "urgency": "1_mes", "rationale": "x"}},
            "action",
        ),
        (
            {"recommendation": {"action": "firmar_adenda", "urgency": "nunca", "rationale": "x"}},
            "urgency",
        ),
        ({"red_flags": ["x" * 260]}, "red_flags"),
        ({"addendum_text": "x" * 4000}, "addendum_text"),
    ],
)
def test_agent_06_schema_strict_validation(corruption, expected_error_substring):
    agent = Agent06AnalistaContratos()
    base = _valid_analysis_for_media()
    base.update(corruption)
    errors = agent._validate_schema(base, ens_category="MEDIA", client_sector="otro")
    assert any(expected_error_substring in e for e in errors), (
        f"No aparece '{expected_error_substring}' en {errors}"
    )


def test_agent_06_schema_enforces_all_required_clauses_for_alta():
    agent = Agent06AnalistaContratos()
    base = _valid_analysis_for_media()
    # base solo cubre BASE + MEDIA+; para ALTA faltan 3 clausulas
    errors = agent._validate_schema(base, ens_category="ALTA", client_sector="otro")
    assert any("clausulas obligatorias" in e for e in errors)


# =======================================================================
# 6) Invalid enum parameters raise ValueError
# =======================================================================


async def test_agent_06_invalid_ens_category_raises(db):
    agent = Agent06AnalistaContratos()
    with pytest.raises(ValueError, match="ens_category invalida"):
        await agent.analyze_provider_contract(
            db,
            contract_text="x",
            provider_name="p", provider_role="hosting",
            criticality="alta", data_processed="ninguno",
            ens_category="MEGA",    # <- invalido
            client_sector="otro",
        )


async def test_agent_06_invalid_provider_role_raises(db):
    agent = Agent06AnalistaContratos()
    with pytest.raises(ValueError, match="provider_role invalido"):
        await agent.analyze_provider_contract(
            db,
            contract_text="x",
            provider_name="p", provider_role="contrabando",
            criticality="alta", data_processed="ninguno",
            ens_category="MEDIA", client_sector="otro",
        )


# =======================================================================
# 7) LLM real - AWS hosting sanidad MEDIA debe detectar gap art. 9 RGPD
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_06_aws_hosting_sanidad_real_llm(db):
    """Ejemplo 1 del prompt: AWS sanidad MEDIA con gap categoria especial."""
    _skip_if_no_api_key()
    agent = Agent06AnalistaContratos()
    result = await agent.analyze_provider_contract(
        db,
        contract_text=AWS_CONTRACT_COMPLETE,
        provider_name="Amazon Web Services EMEA SARL",
        provider_role="hosting",
        criticality="alta",
        data_processed="datos_pacientes",
        ens_category="MEDIA",
        client_sector="sanidad",
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    analysis = result["analysis"]
    # Contrato AWS es solido; score >=60.
    assert analysis["compliance_score"] >= 60
    # Debe detectar gap sectorial categoria especial salud (art. 9) como
    # sector_specific_gap — el contrato generico no aborda datos de salud
    # con profundidad reforzada.
    sector_gaps = analysis["sector_specific_gaps"]
    joined = " ".join(g.get("description", "") for g in sector_gaps).lower()
    assert any(
        keyword in joined
        for keyword in ("art. 9", "art 9", "articulo 9", "categoria especial", "datos de salud", "datos salud", "hce", "historia clin")
    ), f"No detecta gap sanidad art. 9 RGPD. sector_gaps={sector_gaps}"


# =======================================================================
# 8) LLM real - Salesforce fintech ALTA debe detectar gaps DORA
# =======================================================================


SALESFORCE_MSA_TEXT = """
MASTER SERVICES AGREEMENT BETWEEN FINTECH PREMIER S.A. AND SALESFORCE.COM INC.

Section 1: Definitions. "Services" means the Salesforce CRM cloud services.

Section 4: Supplier shall comply with applicable data protection laws.

Section 8: Customer data may be processed in various Salesforce data
centers, including the United States, under the Standard Contractual
Clauses approved by the European Commission.

Section 12: The Agreement may be terminated by either party with 90
days prior written notice.

Section 20: Intellectual property rights in the Services remain with
Salesforce.
"""


@pytest.mark.llm
@pytest.mark.timeout(300)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_06_salesforce_fintech_alta_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent06AnalistaContratos()
    result = await agent.analyze_provider_contract(
        db,
        contract_text=SALESFORCE_MSA_TEXT,
        provider_name="Salesforce.com Inc.",
        provider_role="saas",
        criticality="alta",
        data_processed="datos_clientes",
        ens_category="ALTA",
        client_sector="fintech",
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    analysis = result["analysis"]
    # Score bajo por faltar mayoria de clausulas
    assert analysis["compliance_score"] < 60
    assert analysis["compliance_level"] in {"no_conforme", "critico", "parcial"}

    # Debe detectar gap DORA en sector_specific_gaps
    sector_gaps = analysis["sector_specific_gaps"]
    joined = " ".join(g.get("description", "") for g in sector_gaps).lower()
    assert "dora" in joined, f"No cita DORA en gaps fintech ALTA. sector_gaps={sector_gaps}"

    # La adenda debe citar DORA o DPA
    addendum = analysis["addendum_text"].lower()
    assert "dora" in addendum or "rgpd art. 28" in addendum or "art. 28 rgpd" in addendum


# =======================================================================
# 9) LLM real - prompt caching reduce coste en 2a llamada
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(180)
async def test_agent_06_prompt_caching_reduces_cost(db):
    _skip_if_no_api_key()
    agent = Agent06AnalistaContratos()

    first = await agent.analyze_provider_contract(
        db,
        contract_text=AWS_CONTRACT_COMPLETE,
        provider_name="Provider 1",
        provider_role="hosting",
        criticality="alta",
        data_processed="datos_clientes",
        ens_category="MEDIA",
        client_sector="otro",
    )
    # Cambio minimo en el user msg (provider_name distinto) pero system identico
    second = await agent.analyze_provider_contract(
        db,
        contract_text=AWS_CONTRACT_COMPLETE,
        provider_name="Provider 2",
        provider_role="hosting",
        criticality="alta",
        data_processed="datos_clientes",
        ens_category="MEDIA",
        client_sector="otro",
    )

    # Al menos uno de los 2 lee cache
    assert first["cache_read_input_tokens"] > 0 or second["cache_read_input_tokens"] > 0, (
        f"Ni run 1 ni run 2 leyeron cache. "
        f"first.read={first['cache_read_input_tokens']} "
        f"second.read={second['cache_read_input_tokens']}."
    )
    # Run 2 siempre cache hit
    assert second["cache_read_input_tokens"] > 0
    # Coste run 2 menor — con output ~1500 tokens esperado < 0.04 EUR cacheado
    assert second["cost_eur_estimated"] < 0.040, (
        f"Run 2 coste {second['cost_eur_estimated']:.5f} EUR > 0.040 EUR"
    )
    # Sin fallback
    assert first["fallback_used"] is False
    assert second["fallback_used"] is False
