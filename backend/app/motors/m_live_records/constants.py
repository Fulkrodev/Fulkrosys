"""Constants m_live_records · sub-atom 1.C.C.B.fix v3.9.

Materializa Anexo K plan v3.9 (matriz adaptación per category) · sostiene R28
(adaptación per category sistematizada · NO ad-hoc).

REGISTER_TYPE_REQUIRED_CATEGORIES · single source of truth backend matriz:
    register_type (E-300..E-325) → set categorías ENS aplicables (B · M · A)

Source authoritative:
    - ENS RD 311/2022 Anexo II (73 medidas + bloques applicability per category)
    - Práctica consultiva ENAC (categoría aplicabilidad por tipo registro)
    - Plan FULKRO v3.8 §32 Anexo K.2 (counts: B=17 · M=24 · A=26)

Frontend mirror: `frontend/lib/m_live_records/categories.ts` MUST stay in sync.
"""
from __future__ import annotations

from typing import Literal


CategoryEns = Literal["BASICA", "MEDIA", "ALTA"]


# ============================================================
# Matriz mapping per register_type · categorías ENS aplicables
# ============================================================


REGISTER_TYPE_REQUIRED_CATEGORIES: dict[str, frozenset[CategoryEns]] = {
    # Bloque activos · E-300, E-301, E-302 · TODOS niveles
    "E-300": frozenset(("BASICA", "MEDIA", "ALTA")),
    "E-301": frozenset(("BASICA", "MEDIA", "ALTA")),
    "E-302": frozenset(("BASICA", "MEDIA", "ALTA")),
    # Bloque personas · E-303, E-304 · TODOS niveles
    "E-303": frozenset(("BASICA", "MEDIA", "ALTA")),
    "E-304": frozenset(("BASICA", "MEDIA", "ALTA")),
    # Bloque incidentes
    "E-305": frozenset(("BASICA", "MEDIA", "ALTA")),  # Libro incidentes · TODOS
    "E-306": frozenset(("MEDIA", "ALTA")),  # Vulnerabilidades sistematicas · M+A
    "E-307": frozenset(("BASICA", "MEDIA", "ALTA")),  # Notificaciones autoridades · TODOS
    # Bloque cambios
    "E-308": frozenset(("BASICA", "MEDIA", "ALTA")),  # Libro cambios · TODOS
    "E-309": frozenset(("MEDIA", "ALTA")),  # Cambios materiales · M+A
    "E-310": frozenset(("BASICA", "MEDIA", "ALTA")),  # Excepciones autorizadas · TODOS
    # Bloque proveedores
    "E-311": frozenset(("BASICA", "MEDIA", "ALTA")),  # Inventory proveedores · TODOS
    "E-312": frozenset(("MEDIA", "ALTA")),  # Evaluaciones sistemáticas · M+A
    "E-313": frozenset(("BASICA", "MEDIA", "ALTA")),  # Adendas firmadas · TODOS
    # Bloque backup
    "E-314": frozenset(("BASICA", "MEDIA", "ALTA")),  # Libro backups · TODOS
    "E-315": frozenset(("BASICA", "MEDIA", "ALTA")),  # Pruebas restauracion · TODOS
    "E-316": frozenset(("MEDIA", "ALTA")),  # Verificacion integridad · M+A
    # Bloque continuidad
    "E-317": frozenset(("MEDIA", "ALTA")),  # BCP pruebas · M+A
    "E-318": frozenset(("ALTA",)),  # DRP ejercicios · solo A
    "E-319": frozenset(("ALTA",)),  # RTO/RPO measurements · solo A
    # Bloque auditoria
    "E-320": frozenset(("BASICA", "MEDIA", "ALTA")),  # Auditoría interna · TODOS
    "E-321": frozenset(("MEDIA", "ALTA")),  # Audit externa ENAC · M+A
    "E-322": frozenset(("BASICA", "MEDIA", "ALTA")),  # Hallazgos NC · TODOS
    # Bloque comité
    "E-323": frozenset(("BASICA", "MEDIA", "ALTA")),  # Actas comité · TODOS
    "E-324": frozenset(("BASICA", "MEDIA", "ALTA")),  # Decisiones aprobadas · TODOS
    "E-325": frozenset(("MEDIA", "ALTA")),  # Indicadores SGSI mensuales · M+A
}


# ============================================================
# Helper functions · single source backend matriz
# ============================================================


def is_register_required_for_category(
    register_type: str, category: CategoryEns,
) -> bool:
    """True si register_type es required para una categoría ENS dada.

    Raises ValueError si register_type unknown.
    """
    required_set = REGISTER_TYPE_REQUIRED_CATEGORIES.get(register_type)
    if required_set is None:
        raise ValueError(
            f"Unknown register_type {register_type!r}. "
            f"Valid types: {sorted(REGISTER_TYPE_REQUIRED_CATEGORIES.keys())}"
        )
    return category in required_set


def get_required_registers_for_category(
    category: CategoryEns,
) -> list[str]:
    """Returns lista register_types required para categoría · ordenada ascending."""
    return sorted(
        rt
        for rt, cats in REGISTER_TYPE_REQUIRED_CATEGORIES.items()
        if category in cats
    )


def get_categories_for_register(register_type: str) -> frozenset[CategoryEns]:
    """Returns set categorías para register_type · empty frozenset si unknown."""
    return REGISTER_TYPE_REQUIRED_CATEGORIES.get(register_type, frozenset())


# ============================================================
# Counts esperados per category (Plan v3.8 §32 Anexo K.2)
# ============================================================


COUNTS_PER_CATEGORY: dict[CategoryEns, int] = {
    "BASICA": 17,
    "MEDIA": 24,
    "ALTA": 26,
}
