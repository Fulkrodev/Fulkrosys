"""Tests M08 LLM Capa 3 fallback classifiers (SAN-B.MB-3.ter.3).

Cubre:
- _extract_json tolerant a markdown/prose
- classify_mitre_technique_via_llm: invoked + low confidence + parse + source
- classify_ens_measure_via_llm: invoked + low confidence + parse + source
- retest_zfp_via_llm: 3 verdicts + low confidence → not_applicable
- Wiring: MitreMapper Capa 1+2 fail → LLM Capa 3 invoked
- Wiring: gate4_retest enable_llm_capa3_retest=True → uses LLM
- 3 @pytest.mark.llm real LLM tests (1 por mapper)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.ai.llm_router import LLMResponse
from backend.app.motors.m08_verification.llm_classifier import (
    CONFIDENCE_THRESHOLD,
    _extract_json,
    classify_ens_measure_via_llm,
    classify_mitre_technique_via_llm,
    retest_zfp_via_llm,
)
from backend.app.motors.m08_verification.mitre_mapper import MitreMapper
from backend.app.motors.m08_verification.zfp_engine import ZfpFinding, gate4_retest


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

def _make_finding(
    *, title="SQL injection in login",
    description="Unsanitized user input in /api/login",
    cve_id=None, affected_service="webapp",
    affected_host="srv01", confidence=0.6,
) -> ZfpFinding:
    return ZfpFinding(
        finding_hash="h-" + title[:8],
        title=title,
        description=description,
        severity="high",
        affected_host=affected_host,
        affected_port=443,
        affected_service=affected_service,
        affected_url="https://x/login",
        cve_id=cve_id,
        confidence_score=confidence,
        tool_sources=["nuclei"],
    )


def _mock_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content, model="claude-haiku-4-5",
        prompt_tokens=10, completion_tokens=20, total_tokens=30,
        latency_ms=100.0,
    )


# ════════════════════════════════════════════════════════════════════
# 1. _extract_json edge cases (unit · pure)
# ════════════════════════════════════════════════════════════════════

def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_prose():
    txt = 'Here is the JSON:\n{"verdict": "confirmed", "confidence": 0.9}\nThanks.'
    assert _extract_json(txt) == {"verdict": "confirmed", "confidence": 0.9}


def test_extract_json_markdown_fenced():
    txt = "Result:\n```json\n{\"k\": 42}\n```\nDone."
    assert _extract_json(txt) == {"k": 42}


def test_extract_json_no_json_returns_none():
    assert _extract_json("LLM refused to respond") is None


def test_extract_json_malformed_returns_none():
    assert _extract_json("{not valid json here") is None


# ════════════════════════════════════════════════════════════════════
# 2. classify_mitre_technique_via_llm (mocked LLM)
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def reset_router_singleton():
    """Clear LLMRouter singleton between tests · mock isolation."""
    from backend.app.motors.m08_verification import llm_classifier
    if hasattr(llm_classifier._get_router, "_instance"):
        delattr(llm_classifier._get_router, "_instance")
    yield
    if hasattr(llm_classifier._get_router, "_instance"):
        delattr(llm_classifier._get_router, "_instance")


def test_mitre_llm_high_confidence_returns_techniques(reset_router_singleton):
    fake_response = _mock_llm_response("""{
        "confidence": 0.85,
        "techniques": [
            {"technique_id": "T1190", "tactic": "Initial Access",
             "technique_name": "Exploit Public-Facing Application"}
        ],
        "reasoning": "SQL injection in webapp login"
    }""")
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        result = classify_mitre_technique_via_llm(_make_finding())
    assert len(result) == 1
    assert result[0]["technique_id"] == "T1190"
    assert result[0]["source"] == "llm_capa3"


def test_mitre_llm_low_confidence_returns_empty(reset_router_singleton):
    fake_response = _mock_llm_response('{"confidence": 0.3, "techniques": []}')
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        result = classify_mitre_technique_via_llm(_make_finding())
    assert result == []


def test_mitre_llm_invalid_technique_id_filtered(reset_router_singleton):
    fake_response = _mock_llm_response("""{
        "confidence": 0.9,
        "techniques": [
            {"technique_id": "INVALID", "tactic": "x", "technique_name": "y"},
            {"technique_id": "T1190", "tactic": "x", "technique_name": "y"}
        ]
    }""")
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        result = classify_mitre_technique_via_llm(_make_finding())
    assert len(result) == 1
    assert result[0]["technique_id"] == "T1190"


def test_mitre_mapper_capa12_fail_invokes_capa3_llm(reset_router_singleton):
    """E2E wiring: si Capa 1+2 no matchean, MitreMapper.map() invoca LLM."""
    fake_response = _mock_llm_response("""{
        "confidence": 0.7,
        "techniques": [
            {"technique_id": "T1078", "tactic": "Defense Evasion",
             "technique_name": "Valid Accounts"}
        ]
    }""")
    # Finding sin CVE conocido y sin keywords reconocidas
    finding = _make_finding(
        title="Some unusual issue", description="weird thing",
        cve_id=None, affected_service="custom",
    )
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        mapper = MitreMapper(enable_llm=True)
        result = mapper.map(finding)
    assert len(result) == 1
    assert result[0]["technique_id"] == "T1078"
    assert result[0]["source"] == "llm_capa3"


def test_mitre_mapper_disable_llm_skips_capa3(reset_router_singleton):
    """enable_llm=False · Capa 3 no se invoca · returns []."""
    finding = _make_finding(
        title="Unrecognized issue", description="",
        cve_id=None, affected_service="custom",
    )
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mapper = MitreMapper(enable_llm=False)
        result = mapper.map(finding)
        # LLM not called at all
        mock_router_cls.return_value.complete.assert_not_called()
    assert result == []


# ════════════════════════════════════════════════════════════════════
# 3. classify_ens_measure_via_llm (mocked LLM)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ens_llm_high_confidence_returns_measures(reset_router_singleton):
    fake_response = _mock_llm_response("""{
        "confidence": 0.8,
        "measures": [
            {"measure_code": "op.exp.4", "rationale": "vulnerability mgmt"}
        ]
    }""")
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        result = await classify_ens_measure_via_llm(_make_finding())
    assert len(result) == 1
    assert result[0]["measure_code"] == "op.exp.4"
    assert result[0]["method"] == "llm"
    assert result[0]["source"] == "llm_capa3"
    assert result[0]["confidence"] == 0.80


@pytest.mark.asyncio
async def test_ens_llm_low_confidence_returns_empty(reset_router_singleton):
    fake_response = _mock_llm_response('{"confidence": 0.4, "measures": []}')
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        result = await classify_ens_measure_via_llm(_make_finding())
    assert result == []


@pytest.mark.asyncio
async def test_ens_llm_invalid_code_filtered(reset_router_singleton):
    fake_response = _mock_llm_response("""{
        "confidence": 0.9,
        "measures": [
            {"measure_code": "NOT-VALID-CODE", "rationale": "x"},
            {"measure_code": "mp.if.6", "rationale": "host hardening"}
        ]
    }""")
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        result = await classify_ens_measure_via_llm(_make_finding())
    assert len(result) == 1
    assert result[0]["measure_code"] == "mp.if.6"


# ════════════════════════════════════════════════════════════════════
# 4. retest_zfp_via_llm (mocked LLM)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_retest_llm_returns_confirmed(reset_router_singleton):
    fake_response = _mock_llm_response(
        '{"verdict": "confirmed", "confidence": 0.85, "reasoning": "CVE matches"}'
    )
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        verdict = await retest_zfp_via_llm(_make_finding())
    assert verdict == "confirmed"


@pytest.mark.asyncio
async def test_retest_llm_returns_not_confirmed(reset_router_singleton):
    fake_response = _mock_llm_response(
        '{"verdict": "not_confirmed", "confidence": 0.7, "reasoning": "no evidence"}'
    )
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        verdict = await retest_zfp_via_llm(_make_finding())
    assert verdict == "not_confirmed"


@pytest.mark.asyncio
async def test_retest_llm_low_confidence_not_applicable(reset_router_singleton):
    fake_response = _mock_llm_response(
        '{"verdict": "confirmed", "confidence": 0.3}'
    )
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        verdict = await retest_zfp_via_llm(_make_finding())
    assert verdict == "not_applicable"


@pytest.mark.asyncio
async def test_retest_llm_invalid_verdict_not_applicable(reset_router_singleton):
    fake_response = _mock_llm_response(
        '{"verdict": "weird_value", "confidence": 0.9}'
    )
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        verdict = await retest_zfp_via_llm(_make_finding())
    assert verdict == "not_applicable"


@pytest.mark.asyncio
async def test_gate4_retest_with_enable_llm_capa3_uses_llm(reset_router_singleton):
    """gate4_retest(enable_llm_capa3_retest=True) wires LLM callback."""
    fake_response = _mock_llm_response(
        '{"verdict": "confirmed", "confidence": 0.9}'
    )
    finding = _make_finding(confidence=0.6)  # below 0.85 threshold
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        mock_router_cls.return_value.complete.return_value = fake_response
        await gate4_retest([finding], enable_llm_capa3_retest=True)
    assert finding.zfp_gate4_retest == "confirmed"
    # confidence boosted by +0.25 per gate4 logic
    assert finding.confidence_score == 0.85


@pytest.mark.asyncio
async def test_gate4_retest_default_marks_not_tested(reset_router_singleton):
    """Backwards compat: sin flag y sin callback → not_tested (legacy)."""
    finding = _make_finding(confidence=0.6)
    with patch(
        "backend.app.motors.m08_verification.llm_classifier.LLMRouter"
    ) as mock_router_cls:
        await gate4_retest([finding])  # default: enable_llm_capa3_retest=False
        mock_router_cls.return_value.complete.assert_not_called()
    assert finding.zfp_gate4_retest == "not_tested"
    assert finding.confidence_score == 0.6  # unchanged


# ════════════════════════════════════════════════════════════════════
# 5. @pytest.mark.llm real-LLM smoke tests (1 per mapper · 3 total)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.llm
def test_mitre_llm_real_smoke(reset_router_singleton):
    """Real LLM call · validates structured output contract."""
    finding = _make_finding(
        title="Apache Struts2 OGNL injection",
        description="Server allows arbitrary OGNL expression evaluation in HTTP header.",
    )
    result = classify_mitre_technique_via_llm(finding)
    # Real LLM may or may not classify · just verify structure if non-empty
    for t in result:
        assert "technique_id" in t
        assert "source" in t
        assert t["source"] == "llm_capa3"


@pytest.mark.llm
@pytest.mark.asyncio
async def test_ens_llm_real_smoke(reset_router_singleton):
    """Real LLM call · validates ENS measure code contract."""
    finding = _make_finding(
        title="Outdated TLS 1.0 still enabled",
        description="Server accepts TLS 1.0 connections; should require TLS 1.2+",
    )
    result = await classify_ens_measure_via_llm(finding)
    for m in result:
        assert "measure_code" in m
        assert m["method"] == "llm"
        assert m["source"] == "llm_capa3"


@pytest.mark.llm
@pytest.mark.asyncio
async def test_retest_zfp_llm_real_smoke(reset_router_singleton):
    """Real LLM call · validates verdict contract."""
    finding = _make_finding(confidence=0.6)
    verdict = await retest_zfp_via_llm(finding)
    assert verdict in {"confirmed", "not_confirmed", "not_applicable"}
