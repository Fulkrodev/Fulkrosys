"""Tests Sprint C6 — hooks reactivos + integraciones menores."""
from __future__ import annotations


def test_c6_1_m19_service_has_reactive_hook():
    """M19 service.py debe invocar EscalationService y ChangeRequest en materialize."""
    from pathlib import Path
    src = Path("backend/app/motors/m19_risk/service.py").read_text()
    assert "_trigger_reactive_hooks" in src
    assert "EscalationService" in src
    assert "ChangeRequest" in src
    assert "riesgo_materializado_alto" in src


def test_c6_3_m22_has_8_spanish_regex():
    """M22 data_discovery debe tener 8 patrones españoles."""
    from backend.app.motors.m22_discovery.data_discovery import SENSITIVITY_PATTERNS
    tipos = {p["tipo"] for p in SENSITIVITY_PATTERNS}
    required = {
        "DNI_NIE", "NIF_CIF", "IBAN_ES", "TARJETA_CREDITO",
        "NSS", "TELEFONO_ES", "EMAIL", "DATOS_SALUD",
    }
    assert required.issubset(tipos), f"Faltan: {required - tipos}"


# test_c6_4_m8_attack_heatmap_endpoint_exists — DEMOLIDO Sesion 7.
# El endpoint attack-heatmap pertenecia a M8 v4.2 (multi-agente ReAct con
# attack_graph). M8 v5.1 sustituye attack-heatmap por compliance-heatmap
# (las 73 medidas ENS con tech_status). El nuevo test correspondiente
# vivira en backend/tests/motors/m08_verification/test_heatmap.py.
