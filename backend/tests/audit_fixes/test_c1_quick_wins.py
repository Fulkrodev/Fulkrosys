"""Tests Sprint C1 — Quick wins.

Tests c1_1 y c1_2 (sobre M8 v4.2 integrations_enabled y tool_registry)
demolidos en Sesion 7. Se mantienen c1_3 (M25) y c1_4 (M9) que no
dependen de M8.
"""
from __future__ import annotations


def test_c1_3_m25_hook_certified_to_retainer_code_present():
    """M25 lifecycle_service.py debe invocar RetainerService en CERTIFIED→RETAINER."""
    from pathlib import Path
    src = Path("backend/app/motors/m25_lifecycle/lifecycle_service.py").read_text()
    assert "RetainerService" in src
    assert 'to_state == "RETAINER"' in src
    assert "create_retainer" in src


def test_c1_4_m9_imports_idms_standard_folders():
    """M9 dossier_generator.py referencia STANDARD_FOLDERS de M24 (cross-link)."""
    from pathlib import Path
    src = Path("backend/app/motors/m09_audit_prep/dossier_generator.py").read_text()
    assert "IDMS_STANDARD_FOLDERS" in src
    # Las carpetas M24 (IDMS) alineadas en count con DOSSIER_STRUCTURE M9.
    # 16 = 00-14 (incl 14_Remediacion ADR-055) + 99.
    from backend.app.motors.m24_idms.idms_service import STANDARD_FOLDERS
    from backend.app.motors.m09_audit_prep.dossier_generator import DOSSIER_STRUCTURE
    assert len(STANDARD_FOLDERS) == len(DOSSIER_STRUCTURE) == 16
