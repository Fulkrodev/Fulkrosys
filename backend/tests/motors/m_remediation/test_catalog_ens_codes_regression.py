"""Regresión batch2: los códigos ENS del ACTION_CATALOG deben existir en el
Anexo II RD 311/2022 (antes había mp.s.8 inexistente + mp.info.3 = "Firma
electrónica" mal asignado a cifrado · ADR-031 trazabilidad ENAC)."""
from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311
from backend.app.motors.m_remediation.catalog import ACTION_CATALOG


def test_all_action_catalog_ens_measures_exist_in_anexo_ii():
    valid = set(ANEXO_II_RD311.keys())
    bad: dict[str, list[str]] = {}
    for action, spec in ACTION_CATALOG.items():
        for code in (spec.ens_measures or ()):
            if code not in valid:
                bad.setdefault(action, []).append(code)
    assert not bad, f"Códigos ENS inexistentes en ACTION_CATALOG: {bad}"
