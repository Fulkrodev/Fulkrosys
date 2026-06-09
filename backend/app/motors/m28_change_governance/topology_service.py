"""Motor 28 — Role Topology Library (addendum §8.6).

5 patrones predefinidos. Cada uno describe el reparto de los roles ENS
(Responsable de la Informacion, del Servicio, del Sistema, de la Seguridad)
y la composicion del Comite. Se eligen al cierre de M16 onboarding y se
revisan cuando un MaterialChange afecta a roles.
"""
from __future__ import annotations

from typing import Literal


PatternId = Literal["PATTERN_A", "PATTERN_B", "PATTERN_C", "PATTERN_D", "PATTERN_E"]


TOPOLOGY_LIBRARY: dict[str, dict] = {
    "PATTERN_A": {
        "name": "Sponsor + TI interno + RSEG externo + Comite ligero",
        "best_for": "PYME que internaliza TI pero externaliza la seguridad",
        "roles": {
            "responsable_informacion": "sponsor",
            "responsable_servicio": "sponsor",
            "responsable_sistema": "ti_interno",
            "responsable_seguridad": "consultor_externo",
        },
        "comite": {"composicion": "minima", "frecuencia": "trimestral"},
    },
    "PATTERN_B": {
        "name": "Direccion + MSP + RSEG externo + Comite formal",
        "best_for": "Cliente con MSP gestionando TI completa",
        "roles": {
            "responsable_informacion": "direccion",
            "responsable_servicio": "direccion",
            "responsable_sistema": "msp",
            "responsable_seguridad": "consultor_externo",
        },
        "comite": {"composicion": "formal", "frecuencia": "trimestral"},
    },
    "PATTERN_C": {
        "name": "TI interno + Legal externo + RSEG interno + Comite formal",
        "best_for": "Cliente maduro con equipo TI propio y CISO interno",
        "roles": {
            "responsable_informacion": "direccion",
            "responsable_servicio": "negocio",
            "responsable_sistema": "ti_interno",
            "responsable_seguridad": "ciso_interno",
        },
        "comite": {"composicion": "formal", "frecuencia": "mensual"},
    },
    "PATTERN_D": {
        "name": "Excepcion justificada (RSEG/RS combinados)",
        "best_for": "Micro-PYME con menos de 25 empleados",
        "roles": {
            "responsable_informacion": "sponsor",
            "responsable_servicio": "sponsor",
            "responsable_sistema": "sponsor",
            "responsable_seguridad": "consultor_externo",
        },
        "comite": {"composicion": "ligera", "frecuencia": "anual"},
        "requires_memo": True,
    },
    "PATTERN_E": {
        "name": "Multi-sede / multi-cloud / Categoria ALTA",
        "best_for": "Organizaciones distribuidas con riesgo elevado",
        "roles": {
            "responsable_informacion": "comite",
            "responsable_servicio": "comite",
            "responsable_sistema": "ti_interno",
            "responsable_seguridad": "ciso_interno",
        },
        "comite": {"composicion": "extendida", "frecuencia": "mensual"},
    },
}


def list_patterns() -> list[dict]:
    return [{"id": pid, **info} for pid, info in TOPOLOGY_LIBRARY.items()]


def get_pattern(pattern_id: str) -> dict | None:
    info = TOPOLOGY_LIBRARY.get(pattern_id)
    if info is None:
        return None
    return {"id": pattern_id, **info}


def recommend_pattern(
    sector: str,
    employees: int,
    has_internal_it: bool,
    has_internal_ciso: bool,
    multi_site: bool,
    category: str,
) -> str:
    """Recommend a topology based on simple deterministic heuristics."""
    if multi_site or category == "ALTA":
        return "PATTERN_E"
    if employees < 25:
        return "PATTERN_D"
    if has_internal_ciso:
        return "PATTERN_C"
    if has_internal_it:
        return "PATTERN_A"
    return "PATTERN_B"


def requires_memo(pattern_id: str) -> bool:
    info = TOPOLOGY_LIBRARY.get(pattern_id, {})
    return bool(info.get("requires_memo"))
