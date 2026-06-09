"""Motor 16 — Addendum v2.2 §9.1 extensions.

Añade al onboarding adaptativo:
- route_gate_block: workflow que fuerza seleccion de ruta antes de Fase 1
- role_topology_designer: propone topologia (5 patrones, addendum §8.6)
- overlay_detection_block: detecta PCE/micro-CeENS aplicable
- retainer_profile_predictor: predice perfil retainer (R_LITE/R_STD/R_PLUS/R_CRITICAL)
"""
from __future__ import annotations

from typing import Literal

from backend.app.motors.m27_conformity.service import detect_overlay
from backend.app.motors.m27_conformity.route_machine import RouteType
from backend.app.motors.m28_change_governance.topology_service import (
    get_pattern,
    recommend_pattern,
)


RetainerProfile = Literal["R_LITE", "R_STD", "R_PLUS", "R_CRITICAL"]


def route_gate_block(category: str) -> dict:
    """Determine the route_type the project must lock before Phase 1."""
    if category == "BASICA":
        return {
            "blocked_until_locked": True,
            "required_route_type": RouteType.DECLARATION.value,
            "reason": "Categoria BASICA debe ir por DECLARACION (autoevaluacion)",
        }
    if category in ("MEDIA", "ALTA"):
        return {
            "blocked_until_locked": True,
            "required_route_type": RouteType.CERTIFICATION.value,
            "reason": f"Categoria {category} requiere CERTIFICACION por entidad acreditada ENAC",
        }
    return {
        "blocked_until_locked": True,
        "required_route_type": None,
        "reason": "Categoria pendiente de calculo por Motor 1",
    }


def role_topology_designer(
    sector: str, employees: int, has_internal_it: bool,
    has_internal_ciso: bool, multi_site: bool, category: str,
) -> dict:
    pid = recommend_pattern(sector, employees, has_internal_it, has_internal_ciso, multi_site, category)
    return {
        "recommended_pattern": pid,
        "detail": get_pattern(pid),
        "rationale": _topology_rationale(pid, employees, multi_site, category),
    }


def _topology_rationale(pattern_id: str, employees: int, multi_site: bool, category: str) -> str:
    if pattern_id == "PATTERN_E":
        return f"Multi-sede={multi_site} y/o categoria={category} requieren topologia extendida"
    if pattern_id == "PATTERN_D":
        return f"Plantilla pequena ({employees} empleados): RSEG/RS combinados con memo justificativo"
    if pattern_id == "PATTERN_C":
        return "Cliente con CISO interno: topologia con responsable seguridad propio"
    if pattern_id == "PATTERN_A":
        return "TI interno + RSEG externo: equilibrio comun en PYME"
    return "MSP gestiona TI; RSEG externo y comite formal por defecto"


def overlay_detection_block(sector: str, category: str) -> dict:
    return detect_overlay(sector, category)


def retainer_profile_predictor(
    category: str, employees: int, multi_site: bool, sector: str,
) -> dict:
    sector_lc = (sector or "").lower()
    high_risk_sector = any(k in sector_lc for k in ("salud", "sanid", "fintech", "energi", "publica", "ayunt"))
    if category == "ALTA" or (category == "MEDIA" and high_risk_sector):
        profile: RetainerProfile = "R_CRITICAL"
    elif category == "MEDIA" or multi_site or high_risk_sector:
        profile = "R_PLUS"
    elif category == "BASICA" and employees > 50:
        profile = "R_STD"
    else:
        profile = "R_LITE"
    return {
        "predicted_profile": profile,
        "rationale": (
            f"Categoria={category}, empleados={employees}, multi_site={multi_site}, "
            f"sector={sector}; high_risk_sector={high_risk_sector}"
        ),
    }
