"""CLUSTER 4 Phase 4B · AI Classifier Service tests.

Sesión 3B-2B.8 CLUSTER 4 Phase 4B · pure functional classifier R1 deterministic
+ enhanced keyword matching + ENS measure_code mapping + confidence scoring.

Coverage:
- suggest_classification matches keyword rules · returns measure_codes + tags
- suggest_classification unknown filename returns confidence=0.0 fallback "otro"
- compute_confidence deterministic formula (0/1/2/3+ matches)
- KEYWORD rules diversity (politica, evidencia, registro, informe, contrato)
- content_preview enriches matching beyond filename
- empty/whitespace filename graceful

Pattern 22 cumulative formalized: Enhanced classifier + measure_code mapping
(R1 deterministic · server pre-computes · cliente confirms · admin validates).
"""
from __future__ import annotations

import pytest

from backend.app.motors.m07_evidence.ai_classifier_service import (
    CLASSIFIER_RULES,
    _compute_confidence,
    suggest_classification,
)


# ════════════════════════════════════════════════════════════════════
# Phase 4B · Confidence formula deterministic
# ════════════════════════════════════════════════════════════════════


def test_compute_confidence_zero_matches():
    assert _compute_confidence(0) == 0.0


def test_compute_confidence_one_match():
    assert _compute_confidence(1) == pytest.approx(0.30)


def test_compute_confidence_two_matches():
    assert _compute_confidence(2) == pytest.approx(0.65)


def test_compute_confidence_three_plus_matches():
    assert _compute_confidence(3) == 1.0
    assert _compute_confidence(5) == 1.0


# ════════════════════════════════════════════════════════════════════
# Phase 4B · Filename-based classification scenarios
# ════════════════════════════════════════════════════════════════════


def test_suggest_classification_politica():
    """Filename 'politica_seguridad.pdf' matches rule_politica."""
    result = suggest_classification("politica_seguridad.pdf")
    assert result.suggested_clasificacion == "politica"
    assert result.rule_id == "rule_politica"
    assert "org.4" in result.suggested_measure_codes
    assert "politica" in result.suggested_tags
    assert result.confidence > 0.0


def test_suggest_classification_mfa():
    """Filename 'mfa_log_admins.csv' matches rule_mfa con MFA + autenticacion measure codes."""
    result = suggest_classification("mfa_log_admins.csv")
    assert result.rule_id == "rule_mfa"
    assert "op.acc.6" in result.suggested_measure_codes
    assert "op.acc.5" in result.suggested_measure_codes
    assert "mfa" in result.matched_keywords
    assert result.confidence > 0.0


def test_suggest_classification_backup():
    """Filename 'backup_diario.zip' matches rule_backup measure mp.info.6."""
    result = suggest_classification("backup_diario.zip")
    assert result.rule_id == "rule_backup"
    assert "mp.info.6" in result.suggested_measure_codes
    assert "backup" in result.suggested_tags


def test_suggest_classification_pentest():
    """Filename 'informe_pentest_2026.pdf' matches rule_pentest."""
    result = suggest_classification("informe_pentest_2026.pdf")
    assert result.rule_id == "rule_pentest"
    assert "pentest" in result.matched_keywords
    assert "op.exp.10" in result.suggested_measure_codes


def test_suggest_classification_continuidad_multiple_matches():
    """Filename 'plan_continuidad_drp_bia.pdf' matches multiple keywords (3+)."""
    result = suggest_classification("plan_continuidad_drp_bia.pdf")
    assert result.rule_id == "rule_continuidad"
    assert "op.cont.2" in result.suggested_measure_codes
    # 3+ keywords matched (continuidad + drp + bia) → confidence 1.0
    assert result.confidence == 1.0


# ════════════════════════════════════════════════════════════════════
# Phase 4B · Fallback cuando NO rule match
# ════════════════════════════════════════════════════════════════════


def test_suggest_classification_unknown_filename_fallback(  ):
    """Filename random sin keywords match → confidence=0.0 + 'otro' fallback."""
    result = suggest_classification("zxc_random_file_unknown_xyz.pdf")
    assert result.suggested_clasificacion == "otro"
    assert result.suggested_tipo_documento == "otro"
    assert result.confidence == 0.0
    assert result.suggested_measure_codes == []
    assert result.rule_id is None


def test_suggest_classification_empty_filename():
    """Empty/whitespace filename returns fallback ClassificationSuggestion."""
    for filename in ("", "   ", None):
        if filename is None:
            continue  # type ignored · function expects str
        result = suggest_classification(filename)
        assert result.suggested_clasificacion == "otro"
        assert result.confidence == 0.0


# ════════════════════════════════════════════════════════════════════
# Phase 4B · content_preview enriches matching
# ════════════════════════════════════════════════════════════════════


def test_content_preview_helps_match_when_filename_generic():
    """Filename genérico pero content_preview menciona MAGERIT → match."""
    result = suggest_classification(
        filename="adjunto_001.pdf",
        content_preview="Análisis MAGERIT de riesgo amenaza para sistema X",
    )
    assert result.rule_id == "rule_magerit"
    assert "magerit" in result.matched_keywords


# ════════════════════════════════════════════════════════════════════
# Phase 4B · Rules diversity + integrity
# ════════════════════════════════════════════════════════════════════


def test_classifier_rules_diversity_clasificacion_types():
    """CLASSIFIER_RULES cubren múltiples clasificacion types ENS lifecycle."""
    clasificacion_types = {rule[2] for rule in CLASSIFIER_RULES}
    expected_types = {
        "politica", "procedimiento", "evidencia", "registro",
        "informe", "contrato",
    }
    assert expected_types.issubset(clasificacion_types)


def test_classifier_rules_have_measure_codes():
    """All CLASSIFIER_RULES tienen ≥1 measure_code mapped (ENS canonical)."""
    for rule in CLASSIFIER_RULES:
        rule_id, keywords, _, _, measure_codes, _ = rule
        assert len(measure_codes) >= 1, (
            f"Rule {rule_id} missing measure_codes mapping"
        )
        for mc in measure_codes:
            # Format check · ENS measure code pattern (familia.subfamilia.N or similar)
            assert "." in mc, f"Rule {rule_id} invalid measure_code format: {mc}"


def test_classifier_rules_have_unique_rule_ids():
    """CLASSIFIER_RULES rule_id values são unique."""
    rule_ids = [rule[0] for rule in CLASSIFIER_RULES]
    assert len(rule_ids) == len(set(rule_ids)), "Duplicate rule_id detected"


# ════════════════════════════════════════════════════════════════════
# Phase 4B · ClassificationSuggestion dataclass + to_dict serialization
# ════════════════════════════════════════════════════════════════════


def test_classification_suggestion_to_dict_serializes():
    """to_dict returns JSON-serializable dict (R1 dataclass)."""
    result = suggest_classification("politica_v2.pdf")
    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["filename"] == "politica_v2.pdf"
    assert "suggested_measure_codes" in d
    assert isinstance(d["suggested_measure_codes"], list)
    assert isinstance(d["confidence"], float)


def test_classification_suggestion_dataclass_frozen():
    """ClassificationSuggestion frozen (R1 immutability)."""
    result = suggest_classification("politica.pdf")
    with pytest.raises(Exception):
        result.confidence = 0.5  # frozen dataclass raises
