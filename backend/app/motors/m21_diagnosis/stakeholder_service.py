"""Stakeholder analysis from PKG person nodes.

DIVERGENCIA CONOCIDA (WAVE C2 · 2026-06-16) · NO unificar a la ligera.
Coexisten DOS linajes de stakeholders, ambos vivos y alcanzando la API:

  * PKG (este módulo, ``stakeholder_service.py``): basado en nodos persona
    del grafo PKG (m16). Define 5 roles obligatorios (incluye ``sponsor``).
    Cableado en ``service.run_diagnosis`` (DiagnosisRun clásico).
  * ORM (``stakeholders_service.py``): tabla ``stakeholders`` + 4 roles ENS
    (RI/RS/RSEG/RSis). Cableado en ``paso5_orchestrator.build_summary``.
    Reusa la regla de separación canónica de m30 (roles_ens).

El registry (agente 22) ya marca esta redundancia como ``deprecated``.
Canónico declarado: la tabla ORM ``Stakeholder`` + m30 roles_ens (F0-1).
Unificar = decidir modelo canónico, migrar el 5º rol (``sponsor``) del PKG
al ORM y re-apuntar ``service.run_diagnosis`` — toca la salida de diagnosis
en vivo, por lo que se DIFIERE a un átomo de consolidación m21 dedicado.
Mismo patrón paralelo en process_service vs processes_service y
compliance_service vs cross_compliance_service.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m16_onboarding import pkg_service as pkg

ENS_REQUIRED_ROLES = {
    "sponsor": "Sponsor del proyecto",
    "ri": "Responsable de la Informacion",
    "rs": "Responsable del Servicio",
    "rseg": "Responsable de Seguridad (RSEG)",
    "rsis": "Responsable del Sistema",
}

ADDITIONAL_ROLES = {
    "dpo": "Delegado de Proteccion de Datos",
    "cto": "Director de Tecnologia",
    "ciso": "Director de Seguridad",
    "rrhh": "Responsable de RRHH",
    "legal": "Responsable Legal",
    "compras": "Responsable de Compras",
}


async def analyze_stakeholders(session: AsyncSession, project_id: uuid.UUID) -> dict:
    people = await pkg.get_nodes_by_type(session, project_id, "person")

    roles_found = {}
    people_summary = []
    for p in people:
        props = p.get("properties") or {}
        role = props.get("role", "unknown")
        roles_found[role] = True
        people_summary.append({
            "label": p["label"],
            "role": role,
            "source": props.get("source", "unknown"),
            "node_id": str(p["id"]),
        })

    missing_required = []
    for role_key, role_name in ENS_REQUIRED_ROLES.items():
        if not roles_found.get(role_key):
            missing_required.append({
                "role_key": role_key,
                "role_name": role_name,
                "severity": "critical",
                "recommendation": f"Asignar {role_name} antes de Fase 2.",
            })

    missing_additional = [
        {"role_key": k, "role_name": v, "severity": "informative"}
        for k, v in ADDITIONAL_ROLES.items() if not roles_found.get(k)
    ]

    required_count = len(ENS_REQUIRED_ROLES)
    found_required = sum(1 for r in ENS_REQUIRED_ROLES if roles_found.get(r))
    coverage = round(100.0 * found_required / required_count, 1) if required_count else 0.0

    return {
        "total_people": len(people),
        "people": people_summary,
        "roles_found": list(roles_found.keys()),
        "ens_required_roles_coverage": coverage,
        "missing_required_roles": missing_required,
        "missing_additional_roles": missing_additional,
        "critical_gaps": len(missing_required),
        "verdict": "ok" if not missing_required else "gaps_detected",
    }
