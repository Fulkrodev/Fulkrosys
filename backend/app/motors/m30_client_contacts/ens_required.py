"""ENS_REQUIRED roles · RD 311/2022 art. 11 + sponsor · SAN-E v3.MB-5.0.bis.

Catálogo independiente del existing ``roles_ens.py`` (CCN-STIC 801 con POC +
Comité). Este módulo define exclusivamente los roles que aparecen nombrados
en documentos ENS auto-generados via M6 Document Factory:

* **sponsor** — patrocinador del proyecto ENS (decisor económico/político ·
  PYMEs frecuentemente CEO).
* 5 roles RD 311/2022 art. 11 (a-e):
  * **responsable_informacion** (a) · requisitos seguridad información tratada.
  * **responsable_servicio** (b) · requisitos seguridad servicio prestado.
  * **responsable_seguridad** (c) · mantiene seguridad información + servicios
    (figura clave · firma DdA · firma declaración conformidad).
  * **responsable_sistema** (d) · desarrollo · operación · mantenimiento.
  * **administrador_seguridad** (e) · administra día a día las medidas
    operativas de seguridad.

Q5.3 (Marcos 2026-05-10): roles INVISIBLE cliente. Marcos los maneja desde
admin (existing AssignContactModal MB-3.5 extension). Cliente NO ve estos roles.

Documentos ENS auto-populate stakeholders desde estos contactos:

* E-002 Acta nombramiento roles ENS (no template existing aún · listo cuando se cree)
* E-012 Acta categorización (firmada RSEG)
* E-040 Informe final adecuación ENS (firmada RSEG · template existing)
* E-027 Plan tratamiento riesgos
* E-028 Aprobación riesgo residual (firmada Dirección/Sponsor)
* E-041 Declaración Conformidad ENS Básica
* E-042 Informe Autoevaluación Básica
* E-006 Acta Revisión Dirección
"""
from __future__ import annotations

from typing import Literal


EnsRequiredRole = Literal[
    "sponsor",
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
    "administrador_seguridad",
]

ENS_REQUIRED_ROLES: tuple[EnsRequiredRole, ...] = (
    "sponsor",
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
    "administrador_seguridad",
)

ENS_ROLE_LABELS: dict[EnsRequiredRole, str] = {
    "sponsor": "Sponsor / Patrocinador",
    "responsable_informacion": "Responsable de la Información",
    "responsable_servicio": "Responsable del Servicio",
    "responsable_seguridad": "Responsable de la Seguridad",
    "responsable_sistema": "Responsable del Sistema",
    "administrador_seguridad": "Administrador de la Seguridad del Sistema",
}

ENS_ROLE_DESCRIPTIONS: dict[EnsRequiredRole, str] = {
    "sponsor": (
        "Patrocinador del proyecto ENS · decisor del cliente que dirige la "
        "decisión económica/política."
    ),
    "responsable_informacion": (
        "Determina los requisitos de seguridad de la información tratada · "
        "RD 311/2022 art. 11.a."
    ),
    "responsable_servicio": (
        "Determina los requisitos de seguridad del servicio prestado · "
        "RD 311/2022 art. 11.b."
    ),
    "responsable_seguridad": (
        "Mantiene la seguridad de la información manejada y los servicios "
        "prestados · RD 311/2022 art. 11.c · firma DdA y declaración "
        "conformidad ENS."
    ),
    "responsable_sistema": (
        "Desarrollo · operación · mantenimiento del sistema · "
        "RD 311/2022 art. 11.d."
    ),
    "administrador_seguridad": (
        "Administra día a día las medidas de seguridad operativa · "
        "RD 311/2022 art. 11.e."
    ),
}

# Documentos ENS que requieren stakeholders nombrados pre-firma.
# Usado por validator pre-generation en M6 Document Factory.
DOCUMENTS_REQUIRE_ENS_ROLES: frozenset[str] = frozenset({
    "E-002",  # Acta nombramiento roles ENS
    "E-012",  # Acta categorización (firmada RSEG)
    "E-040",  # Informe final adecuación ENS (firmada RSEG)
    "E-027",  # Plan tratamiento riesgos
    "E-028",  # Aprobación riesgo residual (firmada Dirección/Sponsor)
    "E-041",  # Declaración Conformidad ENS Básica
    "E-042",  # Informe Autoevaluación Básica
    "E-006",  # Acta Revisión Dirección
})


# Sub-atom 1.C.F.4 · Priority/criticality per category ENS (R28 materializado).
# Los 6 roles son REQUIRED RD 311/2022 para TODA categoría · este mapping
# sirve UI rendering (highlight crítico/recomendado/opcional) NO para
# bloquear assignments. Source: AENOR ENS B/M/A audit checklists + Marcos.
ENS_ROLE_PRIORITY_PER_CATEGORY: dict[
    str, dict[EnsRequiredRole, Literal["critical", "recommended", "optional"]]
] = {
    "BASICA": {
        "sponsor": "critical",
        "responsable_informacion": "critical",
        "responsable_seguridad": "critical",
        "responsable_servicio": "recommended",
        "responsable_sistema": "recommended",
        "administrador_seguridad": "optional",
    },
    "MEDIA": {
        "sponsor": "critical",
        "responsable_informacion": "critical",
        "responsable_servicio": "critical",
        "responsable_seguridad": "critical",
        "responsable_sistema": "critical",
        "administrador_seguridad": "recommended",
    },
    "ALTA": {
        "sponsor": "critical",
        "responsable_informacion": "critical",
        "responsable_servicio": "critical",
        "responsable_seguridad": "critical",
        "responsable_sistema": "critical",
        "administrador_seguridad": "critical",
    },
}


def get_priority_for_category(
    category: str | None,
) -> dict[EnsRequiredRole, str]:
    """Devuelve mapping role → priority para una categoría ENS.

    Si ``category`` es None o desconocida, devuelve todos "recommended".
    """
    if category is None:
        return {role: "recommended" for role in ENS_REQUIRED_ROLES}
    return ENS_ROLE_PRIORITY_PER_CATEGORY.get(
        category.upper(),
        {role: "recommended" for role in ENS_REQUIRED_ROLES},
    )
