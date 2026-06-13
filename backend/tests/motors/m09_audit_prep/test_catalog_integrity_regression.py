"""Regresión catálogo (audit 2026-06-13): códigos E-xxx referenciados por los
gates de auditoría que NO existían como plantilla → "missing"/NC falsas
permanentes (E-005, E-006, E-020..E-030, E-605, E-300..E-302). Guarda para que
no se repita: todo código referenciado debe existir en TEMPLATE_REGISTRY (o ser
None donde se permite).
"""
from backend.app.motors.m06_document_factory.template_registry import TEMPLATE_REGISTRY
from backend.app.motors.m09_audit_prep.checklist_service import (
    REQUIRED_DELIVERABLES, REQUIRE_SIGNATURE,
)
from backend.app.motors.m09_audit_prep.internal_auditor import QUESTION_BANK
from backend.app.motors.m10_audit_sim.audit_questions import AUDIT_QUESTIONS

REG = set(TEMPLATE_REGISTRY)


def test_required_deliverables_all_have_templates():
    for cat, lst in REQUIRED_DELIVERABLES.items():
        orphans = [c for c in lst if c not in REG]
        assert orphans == [], f"{cat} orphan deliverable codes: {orphans}"


def test_require_signature_all_have_templates():
    orphans = [c for c in REQUIRE_SIGNATURE if c not in REG]
    assert orphans == [], f"REQUIRE_SIGNATURE orphan codes: {orphans}"


def test_internal_auditor_required_codes_have_templates():
    orphans = [
        (q.get("code"), q.get("code_required")) for q in QUESTION_BANK
        if q.get("code_required") and q["code_required"] not in REG
    ]
    assert orphans == [], f"internal_auditor orphan code_required: {orphans}"


def test_audit_questions_doc_esperado_have_templates_or_none():
    orphans = [
        (k, v.get("documento_esperado")) for k, v in AUDIT_QUESTIONS.items()
        if isinstance(v, dict) and v.get("documento_esperado")
        and v["documento_esperado"] not in REG
    ]
    assert orphans == [], f"audit_questions orphan documento_esperado: {orphans}"
