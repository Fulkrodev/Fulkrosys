"""#39 Ola9 · puente canónico de nomenclatura de categoría ENS (BASICA<->BASICO).

El audit afirmaba un fire-failure del pentest ('ALTA nunca dispara'); es inexacto
(pentest_auto_trigger compara categoria_objetivo=='ALTA' y crea/chequea la run en
'ALTO' consistentemente). Lo real es la colisión de naming, mitigada con este puente.
"""
from __future__ import annotations

from backend.app.core.category_naming import (
    to_project_category,
    to_verification_category,
)


def test_to_verification_category():
    assert to_verification_category("BASICA") == "BASICO"
    assert to_verification_category("MEDIA") == "MEDIO"
    assert to_verification_category("ALTA") == "ALTO"


def test_to_project_category():
    assert to_project_category("BASICO") == "BASICA"
    assert to_project_category("MEDIO") == "MEDIA"
    assert to_project_category("ALTO") == "ALTA"


def test_accepts_both_forms_and_case():
    assert to_verification_category("alto") == "ALTO"  # ya forma m08, lower
    assert to_verification_category("alta") == "ALTO"  # forma proyecto -> m08
    assert to_project_category("alta") == "ALTA"
    assert to_project_category("ALTO") == "ALTA"


def test_unknown_returns_none():
    assert to_verification_category("XXX") is None
    assert to_project_category(None) is None
    assert to_verification_category("") is None


def test_pentest_run_category_matches_gate():
    # #39 · el pentest crea la run en la forma exacta que el gate
    # alta_pentest_cpstic chequea (VerificationRun.category == 'ALTO').
    assert to_verification_category("ALTA") == "ALTO"
