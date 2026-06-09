"""M21 Paso 5 — Stakeholders graph service (Agente 22).

Modela el organigrama como grafo usando la tabla ``stakeholders`` +
``relaciones`` JSONB. El JSONB ``relaciones`` guarda una lista de aristas
tipadas: ``[{"tipo": "REPORTA_A", "target_id": "<uuid>"}, ...]``.

Tipos de relacion:
- REPORTA_A         : persona -> persona (jerarquia)
- TIENE_ROL         : persona -> rol_codigo (string)
- PERTENECE_A       : persona -> unidad (string)
- MIEMBRO_DE        : persona -> comite (string)
- ROL_DELEGA_EN     : rol -> rol (en scope del proyecto)
- UNIDAD_SUPERIOR   : unidad -> unidad

Queries expuestas:
- ``get_ens_responsibles(project_id)``  → los 4 responsables ENS obligatorios
- ``find_decision_chain(stakeholder_id)`` → cadena de reporte hasta direccion
- ``detect_role_conflicts(project_id)`` → personas con roles incompatibles

Extension opcional a Apache AGE: si ``AGE_ENABLED=true`` en env, tras cada
``build_graph`` se emite tambien CREATE en el grafo AGE con el mismo patron
de nodos/aristas. Para simplicidad, esta implementacion es canonica sobre
la tabla ``stakeholders`` (que ya existe en el schema).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.diagnosis import Stakeholder
# F0-1 (Ejecutable 8 Pasada 16): m30_client_contacts es el catálogo CANÓNICO de
# roles ENS. m21 (legacy diagnosis) reusa la regla de separación de m30 para NO
# divergir (la severidad RSEG≠RSis es category-aware · CCN-STIC 801 · P10-F03).
from backend.app.motors.m30_client_contacts.roles_ens import (
    separation_severity_for_category,
)


# ════════════════════════════════════════════════════════════════════
# Tipos y constantes
# ════════════════════════════════════════════════════════════════════

RELATION_TYPES = {
    "REPORTA_A", "TIENE_ROL", "PERTENECE_A", "MIEMBRO_DE",
    "ROL_DELEGA_EN", "UNIDAD_SUPERIOR",
}


ENS_ROLES = {
    "ri": "Responsable de la Informacion",
    "rs": "Responsable del Servicio",
    "rseg": "Responsable de Seguridad (RSEG)",
    "rsis": "Responsable del Sistema",
}


# Roles incompatibles segun CCN-STIC 801: la misma persona NO puede
# acumular estos pares (separacion de funciones).
INCOMPATIBLE_ROLE_PAIRS: list[tuple[str, str]] = [
    ("rseg", "rsis"),         # Seguridad no puede auditar al Sistema si es el mismo
    ("rseg", "dpo"),          # Compliance separation (conflicto interes)
    ("auditor_interno", "rseg"),
    ("auditor_interno", "rsis"),
    ("propietario_dato", "auditor_interno"),
]


@dataclass
class PersonaInput:
    """Datos minimos para crear un stakeholder en el grafo."""
    nombre: str
    cargo: str | None = None
    email: str | None = None
    departamento: str | None = None
    rol_interno: str | None = None  # codigo ENS (rseg, rsis, ri, rs, dpo...)
    poder: int | None = None
    interes: int | None = None
    actitud: str | None = None


@dataclass
class Relation:
    tipo: str
    target: str             # id UUID como string (o codigo si rol/unidad)
    properties: dict[str, Any] | None = None


# ════════════════════════════════════════════════════════════════════
# Build graph
# ════════════════════════════════════════════════════════════════════

async def build_graph(
    db: AsyncSession, project_id: uuid.UUID,
    personas: list[PersonaInput],
    relations: list[dict[str, Any]] | None = None,
) -> list[Stakeholder]:
    """Crea nodos Stakeholder + guarda aristas en JSONB ``relaciones``.

    ``relations`` es una lista de ``{"from": <nombre|email>, "tipo": ..., "target": ...}``.
    El matcher de ``from`` usa nombre o email para resolver a UUIDs recien
    creados.
    """
    created: dict[str, Stakeholder] = {}
    for p in personas:
        s = Stakeholder(
            project_id=project_id,
            nombre=p.nombre,
            cargo=p.cargo,
            email=p.email,
            departamento=p.departamento,
            poder=p.poder,
            interes=p.interes,
            actitud=p.actitud,
            relaciones={"rol_interno": p.rol_interno, "edges": []},
        )
        db.add(s)
        created[p.nombre.lower()] = s
        if p.email:
            created[p.email.lower()] = s
    await db.flush()

    if relations:
        for rel in relations:
            frm = str(rel.get("from") or "").lower()
            origin = created.get(frm)
            if origin is None:
                continue
            tipo = rel.get("tipo")
            target = rel.get("target")
            if tipo not in RELATION_TYPES or not target:
                continue
            # Resolver target (si es nombre/email, convertir a UUID)
            tgt_node = created.get(str(target).lower())
            target_id = str(tgt_node.id) if tgt_node else str(target)
            current = dict(origin.relaciones or {})
            edges = list(current.get("edges") or [])
            edges.append({
                "tipo": tipo,
                "target": target_id,
                "properties": rel.get("properties"),
            })
            current["edges"] = edges
            origin.relaciones = current
            flag_modified(origin, "relaciones")
        await db.flush()

    return list(set(created.values()))


async def list_stakeholders(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[Stakeholder]:
    stmt = select(Stakeholder).where(
        Stakeholder.project_id == project_id,
        Stakeholder.deleted_at.is_(None),
    )
    return list((await db.execute(stmt)).scalars().all())


# ════════════════════════════════════════════════════════════════════
# Queries
# ════════════════════════════════════════════════════════════════════

def _rol_interno(s: Stakeholder) -> str | None:
    rel = s.relaciones or {}
    return rel.get("rol_interno")


async def get_ens_responsibles(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Devuelve el estado de los 4 roles ENS obligatorios.

    Output:
        {
          "ri":   {"asignado": True,  "nombre": "...", "email": "..."},
          "rs":   {...},
          "rseg": {...},
          "rsis": {...},
          "missing": ["rsis"],
          "coverage_pct": 75.0,
        }
    """
    people = await list_stakeholders(db, project_id)
    out: dict[str, Any] = {}
    for code, label in ENS_ROLES.items():
        found = next(
            (s for s in people if _rol_interno(s) == code), None,
        )
        out[code] = {
            "label": label,
            "asignado": bool(found),
            "nombre": found.nombre if found else None,
            "email": found.email if found else None,
            "stakeholder_id": str(found.id) if found else None,
        }
    missing = [k for k in ENS_ROLES if not out[k]["asignado"]]
    out["missing"] = missing
    out["coverage_pct"] = round(
        100.0 * (len(ENS_ROLES) - len(missing)) / len(ENS_ROLES), 1,
    )
    return out


async def find_decision_chain(
    db: AsyncSession, stakeholder_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Cadena REPORTA_A ascendente desde ``stakeholder_id`` hasta raiz."""
    start = await db.get(Stakeholder, stakeholder_id)
    if not start:
        return []
    chain: list[dict[str, Any]] = []
    visited: set[str] = set()
    current: Stakeholder | None = start
    while current and str(current.id) not in visited:
        visited.add(str(current.id))
        chain.append({
            "id": str(current.id),
            "nombre": current.nombre,
            "cargo": current.cargo,
            "rol": _rol_interno(current),
        })
        edges = (current.relaciones or {}).get("edges", [])
        reporta = next(
            (e for e in edges if e.get("tipo") == "REPORTA_A"), None,
        )
        if not reporta:
            break
        try:
            next_id = uuid.UUID(str(reporta["target"]))
        except (ValueError, TypeError):
            break
        current = await db.get(Stakeholder, next_id)
    return chain


async def detect_role_conflicts(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Detecta personas con roles mutuamente incompatibles.

    Una persona puede tener varios roles via edges TIENE_ROL o via el
    campo ``rol_interno`` (el principal). Si sus roles acumulados
    incluyen cualquier par de INCOMPATIBLE_ROLE_PAIRS, se reporta.
    """
    people = await list_stakeholders(db, project_id)
    # Categoría del proyecto → severidad category-aware del par RSEG≠RSis (regla
    # canónica m30 · CCN-STIC 801). MEDIA/ALTA 'mayor'→error · BÁSICA 'menor'→warning.
    cat_row = (await db.execute(sa_text(
        "SELECT categoria_objetivo FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    categoria = cat_row[0] if cat_row else None
    rseg_rsis_severidad = (
        "error" if separation_severity_for_category(categoria) == "mayor"
        else "warning"
    )
    conflicts: list[dict[str, Any]] = []
    for s in people:
        roles: set[str] = set()
        principal = _rol_interno(s)
        if principal:
            roles.add(principal)
        for e in (s.relaciones or {}).get("edges", []):
            if e.get("tipo") == "TIENE_ROL" and e.get("target"):
                roles.add(str(e["target"]).lower())
        for a, b in INCOMPATIBLE_ROLE_PAIRS:
            if a in roles and b in roles:
                # RSEG≠RSis: severidad category-aware (m30 canónico · F0-1).
                # El resto de pares incompatibles → error (conflicto de interés).
                es_rseg_rsis = {a, b} == {"rseg", "rsis"}
                severidad = rseg_rsis_severidad if es_rseg_rsis else "error"
                conflicts.append({
                    "stakeholder_id": str(s.id),
                    "nombre": s.nombre,
                    "roles_conflicto": [a, b],
                    "severidad": severidad,
                    "descripcion": (
                        f"{s.nombre} acumula los roles {a} y {b} que por "
                        f"separacion de funciones (CCN-STIC 801) no deben "
                        f"recaer en la misma persona."
                    ),
                })
    return conflicts


async def build_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Resumen para el informe E-090: cobertura ENS + conflictos + totales."""
    responsables = await get_ens_responsibles(db, project_id)
    conflicts = await detect_role_conflicts(db, project_id)
    people = await list_stakeholders(db, project_id)
    return {
        "total_personas": len(people),
        "ens_responsibles": responsables,
        "conflictos": conflicts,
        "verdict": (
            "ok" if not conflicts and not responsables["missing"]
            else "gaps_detected"
        ),
    }


__all__ = [
    "ENS_ROLES",
    "INCOMPATIBLE_ROLE_PAIRS",
    "PersonaInput",
    "Relation",
    "build_graph",
    "build_summary",
    "detect_role_conflicts",
    "find_decision_chain",
    "get_ens_responsibles",
    "list_stakeholders",
]
