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

from backend.app.motors.m06_document_factory.template_registry import (
    TEMPLATE_REGISTRY,
)


@dataclass(slots=True, frozen=True)
class DocumentationLevel:
    """Definición canónica de un nivel CCN-STIC 805."""

    level: int
    name: str
    description: str
    approver_role: str
    template_codes: tuple[str, ...]


# R25 · los codes de cada nivel se DERIVAN del registry (drift-proof) en vez de
# listas hardcodeadas que se quedaban incompletas (LEVEL_3 listaba 14 de 39 POS).
# Nivel 2 (normativas) = políticas E-1xx salvo la PSI (E-100 · nivel 1) y los
# documentos rectores del SGSI (E-150/160/170/180 · planes/manual, no normativas
# de personal). Nivel 3 (procedimientos) = TODOS los templates type=procedures.
_RECTORES_SGSI = frozenset({"E-150", "E-160", "E-170", "E-180"})

_NORMATIVAS_CODES: tuple[str, ...] = tuple(sorted(
    code for code, meta in TEMPLATE_REGISTRY.items()
    if meta.get("type") == "policies"
    and code.startswith("E-1")
    and code != "E-100"
    and code not in _RECTORES_SGSI
))

_PROCEDURE_CODES: tuple[str, ...] = tuple(sorted(
    code for code, meta in TEMPLATE_REGISTRY.items()
    if meta.get("type") == "procedures"
))


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
    # R25 · derivado del registry (E-1xx normativas · excl. PSI E-100 y rectores
    # E-150/160/170/180). Antes era una lista hardcodeada que omitía E-120/E-122/
    # E-127 y se desincronizaba al añadir normativas.
    template_codes=_NORMATIVAS_CODES,
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
    # R25 · derivado del registry · TODOS los type=procedures (39 POS, incl.
    # E-204-A, E-PF-001, E-IT-001). Antes listaba solo 14 (y con el code mal
    # escrito "E-204A" en vez de "E-204-A") → omitía la mayoría de los POS.
    template_codes=_PROCEDURE_CODES,
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


# ---------------------------------------------------------------------------
# R25 · POS-set acumulativo por categoría ENS (BÁSICA ⊆ MEDIA ⊆ ALTA)
# ---------------------------------------------------------------------------
# Las categorías ENS son acumulativas: un sistema MEDIA exige todo lo de BÁSICA
# más refuerzos, y ALTA todo lo de MEDIA más los suyos. Espeja el patrón ya
# usado para las normativas en policy_signoff_service (POLICIES_BASICA/MEDIA/
# ALTA). Curado (refinable como las políticas); las invariantes (monotonía +
# ALTA == todos los POS + códigos válidos) están blindadas por test.

# Refuerzos solo-ALTA (no aplican en MEDIA). E-235 = sellos de tiempo
# (mp.info.4 · refuerzo solo-ALTA · ver remediación R10).
_POS_ALTA_ONLY: frozenset[str] = frozenset({"E-235"})

# Núcleo operativo exigible ya en BÁSICA (personal · incidentes+evidencias ·
# vulnerabilidades+parches · copias+restauración · revisión de accesos · brechas
# RGPD · destrucción y soportes · info documentada · auditoría interna · no
# conformidades · concienciación/formación).
_POS_BASICA: tuple[str, ...] = (
    "E-200",    # alta de personal
    "E-201",    # baja de personal
    "E-204",    # gestión de incidentes
    "E-204-A",  # recopilación + custodia de evidencias
    "E-205",    # gestión de vulnerabilidades + parches
    "E-206",    # aplicación de parches
    "E-207",    # copias de seguridad + restauración
    "E-208",    # restauración
    "E-210",    # revisión periódica de accesos
    "E-212",    # respuesta a brechas RGPD
    "E-213",    # notificación de brechas a la AEPD
    "E-214",    # destrucción segura
    "E-215",    # gestión de soportes extraíbles
    "E-218",    # auditoría interna del SGSI
    "E-220",    # gestión de no conformidades
    "E-221",    # gestión de la información documentada
    "E-PF-001",  # concienciación y formación (mp.per.3/4)
)


def _basica_pos() -> tuple[str, ...]:
    # Solo los que existen en el registry (defensivo ante renombrados).
    present = set(_PROCEDURE_CODES)
    return tuple(c for c in _POS_BASICA if c in present)


# ALTA = todos los POS del registry. MEDIA = ALTA menos los refuerzos solo-ALTA.
PROCEDURES_ALTA: tuple[str, ...] = _PROCEDURE_CODES
PROCEDURES_MEDIA: tuple[str, ...] = tuple(
    c for c in _PROCEDURE_CODES if c not in _POS_ALTA_ONLY
)
PROCEDURES_BASICA: tuple[str, ...] = _basica_pos()

POS_BY_CATEGORIA: dict[str, tuple[str, ...]] = {
    "BASICA": PROCEDURES_BASICA,
    "MEDIA": PROCEDURES_MEDIA,
    "ALTA": PROCEDURES_ALTA,
}


def procedures_for_categoria(categoria: str) -> tuple[str, ...]:
    """POS (procedimientos) exigibles acumulativamente para la categoría ENS.

    Devuelve el set ACUMULATIVO (BÁSICA ⊆ MEDIA ⊆ ALTA). ``categoria`` se
    normaliza (mayúsculas/acentos). Categoría desconocida → set de BÁSICA
    (conservador · nunca vacío).
    """
    key = (categoria or "").strip().upper().replace("Á", "A")
    return POS_BY_CATEGORIA.get(key, PROCEDURES_BASICA)


def pos_set_summary() -> list[dict]:
    """Resumen serializable del POS-set acumulativo por categoría (frontend)."""
    return [
        {
            "categoria": cat,
            "pos_codes": list(codes),
            "pos_count": len(codes),
        }
        for cat, codes in POS_BY_CATEGORIA.items()
    ]
