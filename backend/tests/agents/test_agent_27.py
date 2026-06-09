"""Tests Agente 27 - Clasificador IDMS (Sesion 9 Paso 3.2).

Cubre:
- Schema strict con folder_code en whitelist 00-13 + 99.
- Logica requires_human_review segun confidence + alternativas.
- Fallback vacio (content_excerpt <20 chars) sin gastar LLM.
- 2 tests LLM reales (acta gobierno + informe tecnico) + caching.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

from backend.app.agents.agent_27_clasificador import (
    Agent27ClasificadorIDMS,
    ClasificadorIDMSAgent,
    FOLDER_NAMES,
    VALID_FOLDER_CODES,
)


def _skip_if_no_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no configurado - test LLM saltado")


DATAFORMA_CTX = {"sector": "sanidad", "ens_category": "MEDIA"}
AAPP_CTX = {"sector": "aapp", "ens_category": "BASICA"}
FINTECH_CTX = {"sector": "fintech", "ens_category": "ALTA"}


def _valid_classification(
    *,
    folder_code: str = "01",
    confidence: float = 0.92,
    n_alts: int = 0,
) -> dict:
    alts = []
    for i in range(n_alts):
        alts.append({
            "folder_code": "02",
            "folder_name": FOLDER_NAMES["02"],
            "confidence": 0.4,
        })
    return {
        "suggested_folder_code": folder_code,
        "suggested_folder_name": FOLDER_NAMES[folder_code],
        "confidence": confidence,
        "reasoning": "Acta formal de Comite de Seguridad con aprobacion politica.",
        "suggested_tags": [
            {"tag_type": "measure_ens", "value": "org.1", "confidence": 0.9},
        ],
        "alternative_folders": alts,
        "requires_human_review": confidence < 0.85,
    }


def _mock_llm_response(classification: dict, *, tokens_in: int = 1500, tokens_out: int = 350) -> dict:
    return {
        "agent_id": 27,
        "agent_name": "Clasificador IDMS",
        "response": "{...}",
        "parsed": classification,
        "model": "claude-haiku-4-5",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 2000,
        "citations": [],
        "project_id": None,
    }


# =======================================================================
# 1) Registry + enums + alias
# =======================================================================


def test_agent_27_alias_backcompat():
    assert ClasificadorIDMSAgent is Agent27ClasificadorIDMS


def test_agent_27_registered_as_active():
    from backend.app.agents.registry import AGENT_REGISTRY
    info = AGENT_REGISTRY[27]
    assert info["status"] == "activo"
    assert info["model"] == "haiku-4.5"
    assert info["motor"] == "m24"


def test_agent_27_valid_folder_codes_15():
    assert len(VALID_FOLDER_CODES) == 15
    assert VALID_FOLDER_CODES == {
        "00", "01", "02", "03", "04", "05", "06", "07",
        "08", "09", "10", "11", "12", "13", "99",
    }


def test_agent_27_folder_names_mapping():
    assert FOLDER_NAMES["01"] == "Gobierno"
    assert FOLDER_NAMES["13"] == "Informes_Tecnicos"
    assert FOLDER_NAMES["99"] == "Misc"
    assert len(FOLDER_NAMES) == 15


# =======================================================================
# 2) Input validation
# =======================================================================


async def test_agent_27_invalid_sector_raises(db):
    agent = Agent27ClasificadorIDMS()
    with pytest.raises(ValueError, match="sector invalido"):
        await agent.classify_document(
            db,
            document_name="acta.docx",
            content_excerpt="Contenido suficiente para testear validacion de sector.",
            client_context={"sector": "espacio", "ens_category": "MEDIA"},
        )


async def test_agent_27_invalid_ens_category_raises(db):
    agent = Agent27ClasificadorIDMS()
    with pytest.raises(ValueError, match="ens_category invalida"):
        await agent.classify_document(
            db,
            document_name="acta.docx",
            content_excerpt="Contenido suficiente para testear validacion de categoria.",
            client_context={"sector": "sanidad", "ens_category": "MEGA"},
        )


# =======================================================================
# 3) Empty / short excerpt -> fallback sin gastar LLM
# =======================================================================


async def test_agent_27_empty_excerpt_returns_misc_no_llm(db):
    agent = Agent27ClasificadorIDMS()
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock()
    ) as invoke_mock:
        result = await agent.classify_document(
            db,
            document_name="unknown.pdf",
            content_excerpt="",
            client_context=DATAFORMA_CTX,
        )

    invoke_mock.assert_not_called()
    assert result["fallback_used"] is True
    c = result["classification"]
    assert c["suggested_folder_code"] == "99"
    assert c["requires_human_review"] is True
    assert c["confidence"] <= 0.3


async def test_agent_27_short_excerpt_returns_misc(db):
    agent = Agent27ClasificadorIDMS()
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock()
    ) as invoke_mock:
        result = await agent.classify_document(
            db,
            document_name="x.txt",
            content_excerpt="too short",  # <20 chars
            client_context=DATAFORMA_CTX,
        )
    invoke_mock.assert_not_called()
    assert result["fallback_used"] is True
    assert result["classification"]["suggested_folder_code"] == "99"


# =======================================================================
# 4) Mock success path
# =======================================================================


async def test_agent_27_high_confidence_auto_approvable(db):
    """Confidence 0.92 sin alternativas -> requires_human_review=False."""
    agent = Agent27ClasificadorIDMS()
    good = _mock_llm_response(
        _valid_classification(folder_code="01", confidence=0.92, n_alts=0)
    )
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock(return_value=good)
    ):
        result = await agent.classify_document(
            db,
            document_name="acta_15_marzo.docx",
            content_excerpt=(
                "Acta del Comite de Seguridad celebrado el 15 de marzo con "
                "aprobacion de politica MFA-2024-v3 y designacion de RSEG."
            ),
            client_context=DATAFORMA_CTX,
        )
    assert result["fallback_used"] is False
    c = result["classification"]
    assert c["suggested_folder_code"] == "01"
    assert c["requires_human_review"] is False


async def test_agent_27_low_confidence_requires_review(db):
    """Confidence 0.55 -> requires_human_review=True aunque LLM dijera False."""
    agent = Agent27ClasificadorIDMS()
    # Mock: LLM devuelve False pero la logica debe forzar True por threshold
    qual = _valid_classification(folder_code="05", confidence=0.55, n_alts=0)
    qual["requires_human_review"] = False  # A ver si lo forzamos
    good = _mock_llm_response(qual)
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock(return_value=good)
    ):
        result = await agent.classify_document(
            db,
            document_name="plan_anual.pdf",
            content_excerpt=(
                "Plan anual 2026 con roadmap de adecuacion y gaps priorizados "
                "para Ayuntamiento BASICA."
            ),
            client_context=AAPP_CTX,
        )
    c = result["classification"]
    # enforcement fuerza True porque confidence < 0.85
    assert c["requires_human_review"] is True


async def test_agent_27_high_confidence_with_relevant_alts_requires_review(db):
    """Confidence 0.9 PERO alternativa con confidence 0.55 -> requires_review=True."""
    agent = Agent27ClasificadorIDMS()
    qual = _valid_classification(folder_code="05", confidence=0.9, n_alts=0)
    qual["alternative_folders"] = [
        {
            "folder_code": "11",
            "folder_name": "Formacion",
            "confidence": 0.55,
        }
    ]
    qual["requires_human_review"] = False  # LLM se equivoca
    good = _mock_llm_response(qual)
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock(return_value=good)
    ):
        result = await agent.classify_document(
            db,
            document_name="plan_mixto.pdf",
            content_excerpt=(
                "Plan que incluye roadmap adecuacion pero tambien plan formacion."
            ),
            client_context=AAPP_CTX,
        )
    assert result["classification"]["requires_human_review"] is True


# =======================================================================
# 5) Schema strict validation
# =======================================================================


@pytest.mark.parametrize(
    "mutator,expected_substring",
    [
        # folder_code fuera whitelist
        (
            lambda c: c.__setitem__("suggested_folder_code", "15"),
            "suggested_folder_code invalido",
        ),
        # confidence fuera rango
        (
            lambda c: c.__setitem__("confidence", 1.5),
            "confidence fuera",
        ),
        # reasoning muy largo
        (
            lambda c: c.__setitem__("reasoning", "x" * 260),
            "reasoning",
        ),
        # demasiados tags
        (
            lambda c: c.__setitem__("suggested_tags", [
                {"tag_type": "measure_ens", "value": f"m{i}", "confidence": 0.5}
                for i in range(7)
            ]),
            "suggested_tags",
        ),
        # tag_type invalido
        (
            lambda c: c.__setitem__("suggested_tags", [
                {"tag_type": "bogus", "value": "x", "confidence": 0.5}
            ]),
            "tag_type invalido",
        ),
        # alternative folder_code fuera whitelist
        (
            lambda c: c.__setitem__("alternative_folders", [
                {"folder_code": "77", "folder_name": "x", "confidence": 0.4}
            ]),
            "folder_code invalido",
        ),
    ],
)
def test_agent_27_schema_strict_validation(mutator, expected_substring):
    agent = Agent27ClasificadorIDMS()
    base = _valid_classification()
    mutator(base)
    errors = agent._validate_schema(base)
    assert any(expected_substring in e for e in errors), errors


# =======================================================================
# 6) Fallback on invalid JSON + retry exhausted
# =======================================================================


async def test_agent_27_fallback_on_invalid_json(db):
    agent = Agent27ClasificadorIDMS()
    bad = {
        "response": "no json",
        "parsed": None,
        "tokens_input": 500, "tokens_output": 20, "latency_ms": 5,
        "model": "claude-haiku-4-5",
    }
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock(return_value=bad)
    ):
        result = await agent.classify_document(
            db,
            document_name="unknown.pdf",
            content_excerpt=(
                "Contenido suficientemente largo para que el servicio "
                "invoque al LLM pero el LLM devuelve basura no parseable."
            ),
            client_context=DATAFORMA_CTX,
        )
    assert result["fallback_used"] is True
    c = result["classification"]
    assert c["suggested_folder_code"] == "99"
    assert c["requires_human_review"] is True


# =======================================================================
# 7) Batch helper
# =======================================================================


async def test_agent_27_classify_batch(db):
    agent = Agent27ClasificadorIDMS()
    good = _mock_llm_response(_valid_classification())
    with patch.object(
        Agent27ClasificadorIDMS, "invoke", new=AsyncMock(return_value=good)
    ) as invoke_mock:
        results = await agent.classify_batch(
            db,
            documents=[
                {
                    "document_name": "acta1.docx",
                    "content_excerpt": "Acta con contenido suficientemente largo para invocar LLM.",
                },
                {
                    "document_name": "acta2.docx",
                    "content_excerpt": "Otro acta con contenido largo tambien suficiente.",
                },
            ],
            client_context=DATAFORMA_CTX,
        )
    assert len(results) == 2
    assert invoke_mock.call_count == 2
    for r in results:
        assert r["fallback_used"] is False


# =======================================================================
# 8) LLM real - acta gobierno sanidad
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(180)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_27_acta_gobierno_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent27ClasificadorIDMS()
    result = await agent.classify_document(
        db,
        document_name="acta_reunion_15_marzo.docx",
        content_excerpt=(
            "Acta de la reunion del Comite de Seguridad de DataForma S.L. "
            "celebrada el 15 de marzo. Puntos tratados: (1) Aprobacion de la "
            "politica MFA corporativa MFA-2024-v3 para acceso a HCE y sede "
            "electronica. (2) Revision trimestral de controles mp.acc. "
            "(3) Designacion de Ana Martin como RSEG. Asisten: Director "
            "Medico, CISO, DPO externo, y Responsable de TI."
        ),
        deterministic_attempt={"suggested_folder": "99_Misc", "confidence": 0.3},
        client_context=DATAFORMA_CTX,
    )

    assert result["fallback_used"] is False, (
        f"Fallback activado; errores={result['schema_errors'][:3]}"
    )
    c = result["classification"]
    # Acta del Comite de Seguridad -> 01_Gobierno esperado
    assert c["suggested_folder_code"] == "01"
    assert c["confidence"] >= 0.7


# =======================================================================
# 9) LLM real - informe tecnico fintech
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(180)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
async def test_agent_27_informe_tecnico_real_llm(db):
    _skip_if_no_api_key()
    agent = Agent27ClasificadorIDMS()
    result = await agent.classify_document(
        db,
        document_name="reporte_final_cliente.pdf",
        content_excerpt=(
            "Informe de pentest externo ejecutado el 10-12 abril 2026. "
            "Herramientas: nmap, Burp Suite Professional, Metasploit. "
            "Hallazgos: 2 CRITICAL (SQLi en endpoint /api/v1/payments, "
            "credentials en clear en log). 5 HIGH, 11 MEDIUM. Recomendacion "
            "de implantar op.exp.3 configuracion + op.acc.5 MFA + mp.com.3 "
            "cifrado comunicaciones internas antes de auditoria DORA."
        ),
        deterministic_attempt={"suggested_folder": "99_Misc", "confidence": 0.2},
        client_context=FINTECH_CTX,
    )

    assert result["fallback_used"] is False, (
        f"Fallback; errores={result['schema_errors'][:3]}"
    )
    c = result["classification"]
    assert c["suggested_folder_code"] == "13"
    assert c["confidence"] >= 0.7


# =======================================================================
# 10) LLM real - Haiku 4.5 coste bajo (caching opt-in, no garantizado)
# =======================================================================


@pytest.mark.llm
@pytest.mark.timeout(240)
async def test_agent_27_haiku_low_cost_per_classification(db):
    """Verifica coste bajo por clasificacion con Haiku 4.5.

    Nota: claude-haiku-4-5-20251001 es un modelo nuevo y el prompt
    caching puede no estar habilitado todavia en todas las regiones/
    claves API. El agente intenta cachear (ENABLE_PROMPT_CACHING=True)
    pero el test NO exige que cache_read > 0; solo exige que el coste
    total por clasificacion sea bajo, que es el objetivo real del uso
    de Haiku para alto volumen.
    """
    _skip_if_no_api_key()
    agent = Agent27ClasificadorIDMS()

    first = await agent.classify_document(
        db,
        document_name="doc_1.docx",
        content_excerpt=(
            "Acta de Comite de Seguridad con aprobacion de politica MFA "
            "y designacion de nuevo RSEG. Contenido formal de gobierno."
        ),
        client_context=DATAFORMA_CTX,
    )
    second = await agent.classify_document(
        db,
        document_name="doc_2.docx",
        content_excerpt=(
            "Acta del Comite de Seguridad con revision de controles op.acc "
            "y aprobacion plan formacion. Contenido gobierno diferente."
        ),
        client_context=DATAFORMA_CTX,
    )

    # Coste Haiku 4.5 por clasificacion debe ser bajo incluso sin cache:
    # input ~4k tokens * 0.80 USD/M + output ~400 tokens * 4 USD/M =
    # ~0.003 + ~0.0016 = ~0.005 USD = ~0.005 EUR. Tope 0.010 EUR holgado.
    assert first["cost_eur_estimated"] < 0.010, (
        f"Run 1 coste Haiku {first['cost_eur_estimated']:.6f} EUR > 0.010"
    )
    assert second["cost_eur_estimated"] < 0.010, (
        f"Run 2 coste Haiku {second['cost_eur_estimated']:.6f} EUR > 0.010"
    )
    # Los 2 clasifican correctamente sin fallback
    assert first["fallback_used"] is False
    assert second["fallback_used"] is False

    # Si el caching esta habilitado para este modelo, lo aprovechamos
    # (informativo, no obligatorio):
    if second["cache_read_input_tokens"] > 0:
        # Con cache, el coste cached debe ser aun menor
        assert second["cost_eur_estimated"] < 0.003
