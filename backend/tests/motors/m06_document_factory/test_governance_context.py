"""R14 · tests del context builder de gobernanza org.2 (parte pura).

La parte con BD (build_governance_context) se ejerce vía la suite de generación
m06 (generate_document la inyecta). Aquí blindamos la lógica pura: fallbacks
nunca-vacíos, +12 meses y el deep-merge (el caller siempre gana, los huecos se
rellenan).
"""
from datetime import date

from backend.app.motors.m06_document_factory.governance_context import (
    PENDIENTE,
    _empty_governance,
    _plus_12m,
    merge_governance_base,
)

_ROLES = (
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
    "administrador_seguridad",
)


def test_empty_governance_never_blank():
    gov = _empty_governance()
    for role in _ROLES:
        assert gov["responsables"][role]["nombre"] == PENDIENTE
        assert gov["responsables"][role]["cargo"]  # cargo canónico, no vacío
    assert gov["comite_seguridad"]["presidente"] == PENDIENTE
    assert gov["dpo"]["nombre"] == PENDIENTE


def test_plus_12m_anual():
    assert _plus_12m(date(2026, 6, 12)) == "2027-06-12"
    # 29-feb cae a 28-feb del año siguiente (no-bisiesto)
    assert _plus_12m(date(2024, 2, 29)) == "2025-02-28"
    assert _plus_12m(None) is None


def test_merge_caller_wins_and_fills_gaps():
    base = _empty_governance()
    base["cliente"] = {"numero_empleados": 30}
    base["proyecto"] = {"proxima_revision": "2027-06-12"}
    caller = {
        # el caller trae cliente parcial (sin numero_empleados) y un rol nombrado
        "cliente": {"razon_social": "ACME SL"},
        "responsables": {"responsable_seguridad": {"nombre": "Ana", "cargo": "CISO"}},
    }
    merged = merge_governance_base(base, caller)
    # caller gana por sub-clave
    assert merged["cliente"]["razon_social"] == "ACME SL"
    assert merged["responsables"]["responsable_seguridad"]["nombre"] == "Ana"
    # base rellena los huecos (deep-merge, no reemplaza el dict entero)
    assert merged["cliente"]["numero_empleados"] == 30
    assert merged["proyecto"]["proxima_revision"] == "2027-06-12"
    # roles no provistos por el caller mantienen el fallback
    assert merged["responsables"]["responsable_sistema"]["nombre"] == PENDIENTE
