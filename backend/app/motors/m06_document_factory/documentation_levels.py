"""4 niveles documentación SGSI canónica · CCN-STIC 805 · SAN-C.MB-10.8.

El RD 311/2022 + CCN-STIC 805 define jerarquía obligatoria:

* **Nivel 1 — Política de Seguridad de la Información (PSI)**
  Estratégico · aprobado órgano superior gobierno · indefinido.
* **Nivel 2 — Normativas (obligatorias para personal)**
  Tácticas · aprobadas RSEG · acuse recibo formal (e.g. uso aceptable,
  contraseñas, teletrabajo, IA generativa, soportes extraíbles, correo,
  acceso internet, clasificación información).
* **Nivel 3 — Procedimientos (operativos)**
  Operacionales · aprobados RSEG/RSIS · ejecutables paso-a-paso (e.g.
  gestión incidentes 817 · gestión cambios · copias seguridad · DRP
  pruebas continuidad · gestión vulnerabilidades · revisión criptográfica).
* **Nivel 4 — Instrucciones técnicas**
  Detalladas · aprobadas técnicos · runbooks · scripts hardening ·
  configuraciones específicas. Habitualmente per cliente / sistema.

Este módulo proporciona el **mapping declarativo** de los templates
existentes en M06 (policies/ + procedures/ + …) al nivel canónico
correspondiente, sin mover los archivos físicos (preservar git history).
Un atom futuro reorganizará la estructura física si Marcos lo prioriza.

Refs: SAN-C.MB-10.8 · CCN-STIC 805
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class DocumentationLevel:
    """Definición canónica de un nivel CCN-STIC 805."""

    level: int
    name: str
    description: str
    approver_role: str
    template_codes: tuple[str, ...]


# Mapping codes existentes M06 templates_registry.py → nivel canónico.
# E100 = PSI (nivel 1) · resto E1xx = normativas (nivel 2) ·
# E2xx = procedimientos (nivel 3) · nivel 4 = vacío hasta primer cliente.

LEVEL_1_PSI = DocumentationLevel(
    level=1,
    name="Política de Seguridad de la Información (PSI)",
    description=(
        "Documento estratégico aprobado por el órgano superior de gobierno. "
        "Define alcance · objetivos · roles · compromiso de la dirección. "
        "Vigencia indefinida con revisión anual."
    ),
    approver_role="Órgano superior / Sponsor ejecutivo",
    template_codes=(
        "E-100",  # PSI
    ),
)

LEVEL_2_NORMATIVAS = DocumentationLevel(
    level=2,
    name="Normativas (obligatorias para personal)",
    description=(
        "Documentos tácticos aprobados por RSEG. Obligatorios para todo "
        "el personal · acuse de recibo formal (mp.per.3 + org.3). "
        "Cubren: uso aceptable · contraseñas · teletrabajo · soportes "
        "extraíbles · correo · acceso internet · clasificación · IA "
        "generativa · BYOD · cifrado · etc."
    ),
    approver_role="Responsable Seguridad (RSEG)",
    template_codes=(
        "E-101",  # control de acceso
        "E-102",  # contraseñas y autenticación
        "E-103",  # uso aceptable de los recursos
        "E-104",  # clasificación y tratamiento de la info
        "E-105",  # tratamiento datos personales RGPD
        "E-106",  # copias de seguridad
        "E-107",  # cifrado y gestión claves
        "E-108",  # gestión de incidentes
        "E-109",  # continuidad del servicio
        "E-110",  # teletrabajo y movilidad
        "E-111",  # uso servicios cloud
        "E-112",  # seguridad relaciones proveedores
        "E-113",  # adquisición de tecnología
        "E-114",  # desarrollo seguro SSDLC
        "E-115",  # gestión de vulnerabilidades
        "E-116",  # gestión de cambios
        "E-117",  # gestión privilegios y PAM
        "E-118",  # BYOD
        "E-119",  # respuesta a brechas datos personales
        "E-121",  # redes y comunicaciones
        "E-123",  # seguridad física
        "E-124",  # seguridad del personal
        "E-125",  # mesa limpia y pantalla limpia
        "E-126",  # borrado seguro y destrucción
    ),
)

LEVEL_3_PROCEDIMIENTOS = DocumentationLevel(
    level=3,
    name="Procedimientos operativos",
    description=(
        "Procedimientos paso-a-paso aprobados por RSEG/RSIS. Operativos "
        "del día a día · ejecutables por personal técnico y operacional. "
        "Cubren: gestión incidentes (CCN-STIC 817) · cambios · "
        "vulnerabilidades CVSS · copias 3-2-1 · DRP · pruebas continuidad · "
        "respuesta brechas RGPD · gestión soportes (CCN-STIC 305/305A) · "
        "auditoría interna · revisión por dirección · baja empleados · "
        "revisión criptográfica (CCN-STIC 807)."
    ),
    approver_role="RSEG + RSIS",
    template_codes=(
        # Identificados desde M06 templates/procedures/ (E2xx)
        "E-200",  # alta de personal
        "E-201",  # baja de personal
        "E-202",  # cambio de rol
        "E-203",  # gestión de cambios
        "E-204",  # gestión de incidentes
        "E-204A",  # recopilación + custodia evidencias
        "E-205",  # gestión vulnerabilidades + parches
        "E-206",  # aplicación de parches
        "E-207",  # copias de seguridad + restauración
        "E-208",  # restauración
        "E-209",  # pruebas continuidad
        "E-210",  # revisión periódica accesos
        "E-211",  # gestión cuentas privilegiadas
        "E-212",  # respuesta a brechas RGPD
        "E-213",  # notificación brechas a AEPD
        # Otros procedures E2xx (lista completa derivada catalog_loader)
    ),
)

LEVEL_4_INSTRUCCIONES = DocumentationLevel(
    level=4,
    name="Instrucciones técnicas",
    description=(
        "Documentos técnicos detallados aprobados por personal técnico. "
        "Runbooks · scripts hardening · configuraciones específicas (CCN-STIC "
        "570/610/853/884/827) · check-lists IT operacional. "
        "Habitualmente desarrolladas per cliente / sistema · no plantillas "
        "genéricas (se generan durante FASE 6 implantación)."
    ),
    approver_role="Personal técnico (administradores sistemas)",
    template_codes=(),  # vacío canónico · per-cliente FASE 6
)


DOCUMENTATION_LEVELS: tuple[DocumentationLevel, ...] = (
    LEVEL_1_PSI,
    LEVEL_2_NORMATIVAS,
    LEVEL_3_PROCEDIMIENTOS,
    LEVEL_4_INSTRUCCIONES,
)


def list_levels() -> list[DocumentationLevel]:
    return list(DOCUMENTATION_LEVELS)


def get_level_for_template(template_code: str) -> DocumentationLevel | None:
    """Devuelve el nivel canónico al que pertenece un template code."""
    for level in DOCUMENTATION_LEVELS:
        if template_code in level.template_codes:
            return level
    return None


def levels_summary() -> list[dict]:
    """Estructura serializable para frontend (4 niveles + counts)."""
    return [
        {
            "level": lvl.level,
            "name": lvl.name,
            "description": lvl.description,
            "approver_role": lvl.approver_role,
            "template_codes": list(lvl.template_codes),
            "template_count": len(lvl.template_codes),
        }
        for lvl in DOCUMENTATION_LEVELS
    ]
