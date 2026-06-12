"""Tests 4 niveles documentación CCN-STIC 805 · SAN-C.MB-10.8."""
from __future__ import annotations

from backend.app.motors.m06_document_factory.documentation_levels import (
    DOCUMENTATION_LEVELS,
    get_level_for_template,
    levels_summary,
    list_levels,
)


def test_exactly_4_levels_canonical():
    """CCN-STIC 805 define exactamente 4 niveles."""
    levels = list_levels()
    assert len(levels) == 4
    assert [l.level for l in levels] == [1, 2, 3, 4]


def test_level_1_contains_psi_only():
    """Nivel 1 PSI · solo E-100."""
    psi = next(l for l in DOCUMENTATION_LEVELS if l.level == 1)
    assert psi.template_codes == ("E-100",)
    assert "PSI" in psi.name


def test_level_2_normativas_contains_e1xx():
    """Nivel 2 normativas · E-101 a E-126 (sin E-100)."""
    normativas = next(l for l in DOCUMENTATION_LEVELS if l.level == 2)
    assert "E-101" in normativas.template_codes
    assert "E-126" in normativas.template_codes
    assert "E-100" not in normativas.template_codes


def test_level_3_procedimientos_complete():
    """Nivel 3 procedimientos · E-2xx + POS separados (R25 drift-proof).

    Tras R25 el Nivel 3 se deriva del registry (todos los type=procedures), lo
    que incluye además de la serie E-2xx los POS separados de su .md padre en
    R13 (E-PF-001 concienciación, E-IT-001 hardening · codes no-E2xx).
    """
    procs = next(l for l in DOCUMENTATION_LEVELS if l.level == 3)
    assert "E-204" in procs.template_codes  # gestión incidentes (E-2xx)
    assert "E-PF-001" in procs.template_codes  # split R13 · no es E-2xx
    assert "E-IT-001" in procs.template_codes  # split R13 · no es E-2xx
    # el grueso sigue siendo la serie E-2xx
    assert sum(c.startswith("E-2") for c in procs.template_codes) >= 30


def test_level_4_instrucciones_empty_per_cliente():
    """Nivel 4 instrucciones técnicas · vacío canónico (per cliente FASE 6)."""
    instr = next(l for l in DOCUMENTATION_LEVELS if l.level == 4)
    assert instr.template_codes == ()


def test_get_level_for_template_known_codes():
    assert get_level_for_template("E-100").level == 1
    assert get_level_for_template("E-101").level == 2
    assert get_level_for_template("E-204").level == 3
    assert get_level_for_template("nonexistent") is None


def test_levels_summary_serializable():
    summary = levels_summary()
    assert len(summary) == 4
    keys_required = {
        "level", "name", "description", "approver_role",
        "template_codes", "template_count",
    }
    for entry in summary:
        assert keys_required.issubset(entry.keys())
        assert entry["template_count"] == len(entry["template_codes"])


def test_no_template_code_in_multiple_levels():
    """Un template no debe estar en 2 niveles a la vez."""
    seen: set[str] = set()
    for lvl in DOCUMENTATION_LEVELS:
        for code in lvl.template_codes:
            assert code not in seen, f"{code} aparece en múltiples niveles"
            seen.add(code)
