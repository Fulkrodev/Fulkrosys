"""R25 · niveles de documentación drift-proof + POS-set acumulativo.

Blinda que LEVEL_2/LEVEL_3 ya NO omiten documentos (se derivan del registry) y
que el POS-set por categoría es acumulativo (BÁSICA ⊆ MEDIA ⊆ ALTA).
"""
from backend.app.motors.m06_document_factory.documentation_levels import (
    PROCEDURES_ALTA,
    PROCEDURES_BASICA,
    PROCEDURES_MEDIA,
    get_level_for_template,
    procedures_for_categoria,
)
from backend.app.motors.m06_document_factory.template_registry import (
    TEMPLATE_REGISTRY,
)

_ALL_PROCS = {c for c, m in TEMPLATE_REGISTRY.items() if m.get("type") == "procedures"}
_ALL_POLICIES = {c for c, m in TEMPLATE_REGISTRY.items() if m.get("type") == "policies"}


def test_level3_includes_every_procedure():
    """Drift guard: TODO procedimiento del registry está en Nivel 3."""
    for code in _ALL_PROCS:
        lvl = get_level_for_template(code)
        assert lvl is not None and lvl.level == 3, f"{code} no está en Nivel 3"


def test_level3_includes_new_split_procedures():
    """E-PF-001 / E-IT-001 / E-204-A presentes (regresión R13/R25)."""
    for code in ("E-PF-001", "E-IT-001", "E-204-A"):
        lvl = get_level_for_template(code)
        assert lvl is not None and lvl.level == 3, f"{code} falta en Nivel 3"


def test_level2_completa_y_sin_psi_ni_rectores():
    lvl100 = get_level_for_template("E-100")
    assert lvl100 is not None and lvl100.level == 1  # PSI es nivel 1, no 2
    for code in ("E-150", "E-160", "E-170", "E-180"):
        assert get_level_for_template(code) is None  # rectores NO son normativas
    # normativas antes omitidas ahora presentes
    for code in ("E-120", "E-122", "E-127"):
        if code in _ALL_POLICIES:
            lvl = get_level_for_template(code)
            assert lvl is not None and lvl.level == 2, f"{code} falta en Nivel 2"


def test_pos_set_acumulativo_monotono():
    basica, media, alta = set(PROCEDURES_BASICA), set(PROCEDURES_MEDIA), set(PROCEDURES_ALTA)
    assert basica <= media <= alta, "POS-set no es acumulativo BÁSICA⊆MEDIA⊆ALTA"
    assert alta == _ALL_PROCS, "ALTA debe exigir todos los POS"
    # E-235 (sellos · refuerzo solo-ALTA) en ALTA pero NO en MEDIA
    assert "E-235" in alta and "E-235" not in media


def test_pos_codes_todos_validos():
    """Ningún POS curado de BÁSICA es un code fantasma."""
    for code in PROCEDURES_BASICA:
        assert code in _ALL_PROCS, f"{code} de BÁSICA no existe en el registry"


def test_procedures_for_categoria_normaliza():
    assert procedures_for_categoria("básica") == PROCEDURES_BASICA
    assert procedures_for_categoria("MEDIA") == PROCEDURES_MEDIA
    assert procedures_for_categoria("Alta") == PROCEDURES_ALTA
    # desconocida -> BÁSICA (conservador, nunca vacío)
    assert procedures_for_categoria("xxx") == PROCEDURES_BASICA
    assert len(procedures_for_categoria("")) > 0
