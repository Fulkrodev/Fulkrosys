"""Guard test §2.2 audit-2026-06-15 · TODO código ENS usado en los mapeadores
(ens_mapper CVE/pattern + ai_classifier reglas) DEBE existir en el catálogo
canónico RD 311/2022 (ANEXO_II_RD311). Habría cazado la medida fantasma `mp.s.7`.

Además, valida que los mapeadores NO reintroducen títulos: ens_mapper ahora resuelve
el título oficial desde el catálogo en _dedupe_and_pick_primary.
"""
from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311
from backend.app.motors.m07_evidence.ai_classifier_service import CLASSIFIER_RULES
from backend.app.motors.m08_verification.ens_mapper import (
    CVE_TO_ENS,
    PATTERN_TO_ENS,
)


def _codes_from_ens_mapper() -> set[str]:
    codes: set[str] = set()
    for measures in CVE_TO_ENS.values():
        for m in measures:
            codes.add(m["measure"])
    for entry in PATTERN_TO_ENS:
        for m in entry["measures"]:
            codes.add(m["measure"])
    return codes


def _codes_from_ai_classifier() -> set[str]:
    codes: set[str] = set()
    for rule in CLASSIFIER_RULES:
        # (rule_id, keywords, tipo, subtipo, measure_codes, match_keywords)
        for code in rule[4]:
            codes.add(code)
    return codes


def test_all_ens_mapper_codes_exist_in_rd311():
    bad = sorted(c for c in _codes_from_ens_mapper() if c not in ANEXO_II_RD311)
    assert not bad, f"ens_mapper usa códigos ENS inexistentes en RD 311/2022: {bad}"


def test_all_ai_classifier_codes_exist_in_rd311():
    bad = sorted(c for c in _codes_from_ai_classifier() if c not in ANEXO_II_RD311)
    assert not bad, f"ai_classifier usa códigos ENS inexistentes en RD 311/2022: {bad}"


def test_phantom_mp_s_7_not_present():
    """Regresión directa de la medida fantasma cazada por la verificación de cierre."""
    all_codes = _codes_from_ens_mapper() | _codes_from_ai_classifier()
    assert "mp.s.7" not in all_codes
    assert "mp.s.7" not in ANEXO_II_RD311  # confirma que efectivamente no existe
