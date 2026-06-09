"""Roles ENS canónicos + validación segregación funcional (CCN-STIC 801).

El RD 311/2022 + CCN-STIC 801 definen 4 roles ENS obligatorios + POC + Comité:

* **RI** — Responsable de la Información (responsable de las decisiones sobre
  qué información puede recoger, tratarse y comunicarse)
* **RS** — Responsable del Servicio (responsable de los servicios prestados
  por el sistema y de la calidad de los mismos)
* **RSEG** — Responsable de Seguridad / CISO (gestión de la seguridad)
* **RSIS** — Responsable del Sistema (operación día a día del sistema)
* **POC** — Punto de Contacto ante CCN-CERT (notificación incidentes)
* **Miembro Comité Seguridad** — recomendable Básica · obligatorio Media/Alta

Restricción CCN-STIC 801: **RSEG y RSIS NO pueden recaer en la misma persona**
(separación funcional · gestión vs operación). La auditoría ENAC marca esta
violación como **no-conformidad mayor**.

Este módulo provee:

* ``ROLES_ENS_CANONICOS`` enum
* ``validate_role_segregation(client_id, db)`` async function que devuelve
  lista de violaciones (vacía si OK)
* ``has_required_roles(client_id, db)`` async para detectar roles ausentes
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.models import ClientContact


class RolEns(str, Enum):
    """5 roles canónicos ENS + 1 miembro comité (CCN-STIC 801).

    Los valores coinciden con ``role_category`` en ``client_contacts``.
    """

    RI = "responsable_informacion"
    RS = "responsable_servicio"
    RSEG = "responsable_seguridad"
    RSIS = "responsable_sistema"
    POC = "punto_contacto_ccn"
    MIEMBRO_COMITE = "miembro_comite_seguridad"


# Aliases legacy (Bloque 1 schemas.RoleCategory) que también cuentan como rol ENS
LEGACY_RSEG_ALIASES: set[str] = {"rseg", "ciso"}


# Roles obligatorios per categoría de sistema ENS
REQUIRED_ROLES_BASICA: set[RolEns] = {RolEns.RI, RolEns.RS, RolEns.RSEG, RolEns.RSIS}
REQUIRED_ROLES_MEDIA: set[RolEns] = REQUIRED_ROLES_BASICA | {RolEns.POC}
REQUIRED_ROLES_ALTA: set[RolEns] = REQUIRED_ROLES_MEDIA | {RolEns.MIEMBRO_COMITE}


@dataclass(slots=True)
class RoleSegregationViolation:
    """Una violación detectada en la segregación de roles ENS."""

    rule: str
    severity: str  # "mayor" | "menor"
    detail: str
    contact_ids: list[uuid.UUID]


@dataclass(slots=True)
class RoleAssignmentReport:
    """Reporte completo de asignación + violaciones para un cliente."""

    client_id: uuid.UUID
    assigned_roles: dict[str, list[uuid.UUID]]
    missing_roles: list[str]
    violations: list[RoleSegregationViolation]
    compliant: bool


def _is_rseg_role(role_category: str) -> bool:
    """Acepta ``responsable_seguridad`` (canon ENS) o aliases legacy ``rseg``/``ciso``."""
    return role_category == RolEns.RSEG.value or role_category in LEGACY_RSEG_ALIASES


def _is_rsis_role(role_category: str) -> bool:
    return role_category == RolEns.RSIS.value


def separation_severity_for_category(categoria: str | None) -> str:
    """Severidad canónica de la violación de separación RSEG≠RSis según categoría.

    CCN-STIC 801: en MEDIA/ALTA la separación gestión(RSEG)/operación(RSIS) es
    obligatoria → ``"mayor"`` (no-conformidad ENAC); en BÁSICA los roles pueden
    acumularse en entidades pequeñas con medida compensatoria → ``"menor"``.

    FUENTE ÚNICA (P10-F03 · Ejecutable 8 Pasada 16 F0-1): m30 es el catálogo
    canónico de roles ENS · m21 (legacy diagnosis) reusa esta función para NO
    divergir en la regla de separación.
    """
    return "mayor" if (categoria or "").upper() in {"MEDIA", "ALTA"} else "menor"


async def validate_role_segregation(
    db: AsyncSession,
    client_id: uuid.UUID,
    target_category: str = "BASICA",
) -> RoleAssignmentReport:
    """Valida segregación de roles ENS para un cliente.

    Reglas:

    1. **CCN-STIC 801**: RSEG y RSIS deben ser personas distintas (no mismo email
       ni mismo contact_id). Severity = mayor.
    2. **Roles obligatorios per categoría**: BÁSICA exige {RI, RS, RSEG, RSIS} ·
       MEDIA añade POC · ALTA añade Comité Seguridad. Severity = menor para
       missing role.

    Args:
        db: AsyncSession con tenant_context aplicado (RLS).
        client_id: UUID del cliente.
        target_category: "BASICA" | "MEDIA" | "ALTA" para determinar
            requeridos.

    Returns:
        RoleAssignmentReport con lista de violaciones detectadas.
    """
    stmt = select(ClientContact).where(
        ClientContact.client_id == client_id,
        ClientContact.is_active.is_(True),
        ClientContact.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    contacts = result.scalars().all()

    assigned_roles: dict[str, list[uuid.UUID]] = {}
    rseg_contacts: list[ClientContact] = []
    rsis_contacts: list[ClientContact] = []

    for c in contacts:
        cat = c.role_category
        assigned_roles.setdefault(cat, []).append(c.id)
        if _is_rseg_role(cat):
            rseg_contacts.append(c)
        if _is_rsis_role(cat):
            rsis_contacts.append(c)

    violations: list[RoleSegregationViolation] = []

    cat_norm = target_category.upper()

    # P10-F03 (Ejecutable 8 Pasada 16): la severidad de la separación RSEG≠RSIS
    # es CATEGORY-AWARE. CCN-STIC 801 exige separación de gestión (RSEG) y
    # operación (RSIS); en MEDIA/ALTA es obligatoria → no-conformidad MAYOR. En
    # BÁSICA los roles pueden acumularse en pocas personas (entidades pequeñas)
    # → WARNING (menor) admitiendo una medida compensatoria documentada.
    _separacion_obligatoria = cat_norm in {"MEDIA", "ALTA"}
    _sep_severity = separation_severity_for_category(cat_norm)

    # Regla 1 · RSEG ≠ RSIS (CCN-STIC 801)
    # Detección de "misma persona": mismo email, mismo contact_id, o mismo
    # full_name normalizado (whitespace + lowercase). El unique constraint
    # (client_id, email) bloquea la creación de 2 contactos con mismo email,
    # por lo que el caso más realista en producción es full_name idéntico
    # con emails distintos (e.g., personal vs corporativo).
    for r in rseg_contacts:
        r_name = (r.full_name or "").strip().lower()
        for s in rsis_contacts:
            s_name = (s.full_name or "").strip().lower()
            same_email = r.email and r.email == s.email
            same_id = r.id == s.id
            same_name = r_name and s_name and r_name == s_name
            if same_email or same_id or same_name:
                if _separacion_obligatoria:
                    _consec = (
                        f"CCN-STIC 801 exige personas distintas para gestión "
                        f"(RSEG) y operación (RSIS) en categoría {cat_norm}. "
                        f"No-conformidad MAYOR en auditoría ENAC."
                    )
                else:
                    _consec = (
                        "En categoría BÁSICA la acumulación es admisible si se "
                        "documenta una medida compensatoria (revisión por "
                        "tercero independiente). CCN-STIC 801."
                    )
                violations.append(
                    RoleSegregationViolation(
                        rule="CCN-STIC-801",
                        severity=_sep_severity,
                        detail=(
                            f"Violación segregación funcional: '{r.full_name}' "
                            f"actúa como RSEG y RSIS simultáneamente "
                            f"(emails {r.email!r} y {s.email!r}). {_consec}"
                        ),
                        contact_ids=[r.id, s.id],
                    )
                )

    # Regla 2 · Roles obligatorios per categoría
    if cat_norm == "ALTA":
        required = REQUIRED_ROLES_ALTA
    elif cat_norm == "MEDIA":
        required = REQUIRED_ROLES_MEDIA
    else:
        required = REQUIRED_ROLES_BASICA

    missing_roles: list[str] = []
    for role in required:
        # Considera aliases legacy para RSEG
        present = any(
            _is_rseg_role(cat) if role == RolEns.RSEG else cat == role.value
            for cat in assigned_roles
        )
        if not present:
            missing_roles.append(role.value)
            violations.append(
                RoleSegregationViolation(
                    rule="CCN-STIC-801-ROL-AUSENTE",
                    severity="menor",
                    detail=(
                        f"Rol obligatorio no asignado: {role.value} "
                        f"(requerido para categoría {cat_norm})"
                    ),
                    contact_ids=[],
                )
            )

    return RoleAssignmentReport(
        client_id=client_id,
        assigned_roles=assigned_roles,
        missing_roles=missing_roles,
        violations=violations,
        compliant=not violations,
    )
