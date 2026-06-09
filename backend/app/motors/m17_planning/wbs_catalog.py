"""Catalogo WBS por categoria ENS (M17).

Catalogo representativo (~36 tareas) que cubre fases 0-8. Escalable a
~150 BASICA / ~250 MEDIA / ~350 ALTA anadiendo plantillas.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WBSTaskTemplate:
    code: str
    name: str
    phase: int  # 0-8
    effort_marcos_h: float
    effort_platform_h: float
    duration_days: int
    responsible: str  # "marcos"|"cliente"|"plataforma"|"mixto"
    dependencies: list[str] = field(default_factory=list)
    deliverable: str | None = None
    applies_to: list[str] = field(default_factory=list)


WBS_CATALOG: list[WBSTaskTemplate] = [
    # === FASE 0 — ARRANQUE ===
    WBSTaskTemplate(
        "WBS-001", "Reunión de arranque", 0,
        2.0, 0, 1, "marcos", [], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-002", "Definición de alcance", 0,
        3.0, 0.5, 2, "marcos", ["WBS-001"], "E-005", ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-003", "Designación roles ENS", 0,
        1.0, 0.5, 1, "mixto", ["WBS-001"], "E-002", ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-004", "Constitución Comité Seguridad", 0,
        1.5, 0.5, 1, "mixto", ["WBS-003"], "E-003", ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-005", "Plan de proyecto", 0,
        0.5, 2.0, 1, "plataforma", ["WBS-002"], None, ["BASICA", "MEDIA", "ALTA"],
    ),

    # === FASE 1 — DIAGNOSTICO ===
    WBSTaskTemplate(
        "WBS-010", "Onboarding adaptativo", 1,
        1.0, 4.0, 5, "mixto", ["WBS-005"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-011", "Discovery técnico (M22)", 1,
        0.5, 8.0, 3, "plataforma", ["WBS-010"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-012", "Diagnóstico organizativo (M21)", 1,
        1.0, 4.0, 3, "plataforma", ["WBS-010"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-013", "Categorización del sistema", 1,
        2.0, 1.0, 2, "marcos", ["WBS-010"], "E-012", ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-014", "Informe diagnóstico inicial", 1,
        2.0, 3.0, 3, "plataforma",
        ["WBS-011", "WBS-012", "WBS-013"], None, ["MEDIA", "ALTA"],
    ),

    # === FASE 2 — PLANIFICACION ===
    WBSTaskTemplate(
        "WBS-020", "Análisis de riesgos MAGERIT", 2,
        8.0, 12.0, 10, "mixto", ["WBS-013"], "E-050", ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-021", "Declaración de aplicabilidad", 2,
        3.0, 2.0, 3, "marcos", ["WBS-020"], "E-040", ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-022", "Gap analysis", 2,
        2.0, 4.0, 3, "plataforma", ["WBS-021"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-023", "Plan de adecuación", 2,
        3.0, 2.0, 5, "marcos", ["WBS-022"], None, ["BASICA", "MEDIA", "ALTA"],
    ),

    # === FASE 3 — IMPLEMENTACION ===
    WBSTaskTemplate(
        "WBS-030", "Redacción Política de Seguridad", 3,
        2.0, 3.0, 3, "plataforma", ["WBS-023"], "E-001", ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-031", "Redacción políticas operativas (E-1XX)", 3,
        4.0, 8.0, 10, "plataforma", ["WBS-023"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-032", "Redacción procedimientos (E-2XX)", 3,
        6.0, 12.0, 15, "plataforma", ["WBS-031"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-033", "Implementación controles técnicos", 3,
        8.0, 4.0, 20, "mixto", ["WBS-022"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-034", "Configuración sistemas según ENS", 3,
        6.0, 2.0, 15, "cliente", ["WBS-033"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-035", "BIA + Plan de continuidad", 3,
        4.0, 4.0, 10, "mixto", ["WBS-020"], "E-400", ["MEDIA", "ALTA"],
    ),

    # === FASE 4 — VERIFICACION ===
    WBSTaskTemplate(
        "WBS-040", "Pentest externo (M8)", 4,
        3.0, 16.0, 5, "plataforma", ["WBS-033"], "E-702", ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-041", "Pentest interno (M8)", 4,
        2.0, 16.0, 5, "plataforma", ["WBS-040"], "E-703", ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-042", "Red Team (M8)", 4,
        5.0, 24.0, 10, "plataforma", ["WBS-041"], "E-704", ["ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-043", "Simulacro phishing", 4,
        1.0, 4.0, 3, "plataforma", ["WBS-040"], "E-705", ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-044", "Remediación hallazgos", 4,
        4.0, 2.0, 10, "mixto",
        ["WBS-040", "WBS-041"], None, ["MEDIA", "ALTA"],
    ),

    # === FASE 5 — FORMACION ===
    WBSTaskTemplate(
        "WBS-050", "Plan de formación", 5,
        2.0, 2.0, 3, "marcos", ["WBS-031"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-051", "Sesiones formación personal", 5,
        4.0, 1.0, 5, "marcos", ["WBS-050"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-052", "Simulacro tabletop", 5,
        2.0, 2.0, 2, "marcos", ["WBS-035"], None, ["MEDIA", "ALTA"],
    ),

    # === FASE 6 — GO-LIVE ===
    WBSTaskTemplate(
        "WBS-060", "Auditoría interna (M10)", 6,
        3.0, 8.0, 5, "plataforma",
        ["WBS-044", "WBS-051"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-061", "Corrección no conformidades", 6,
        4.0, 2.0, 10, "mixto", ["WBS-060"], None, ["MEDIA", "ALTA"],
    ),

    # === FASE 7 — CERTIFICACION ===
    WBSTaskTemplate(
        "WBS-070", "Preparación dossier auditoría (M9)", 7,
        2.0, 6.0, 3, "plataforma", ["WBS-061"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-071", "Coaching pre-auditoría", 7,
        3.0, 1.0, 3, "marcos", ["WBS-070"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-072", "Auditoría externa (certificadora)", 7,
        8.0, 0, 10, "marcos",
        ["WBS-070", "WBS-071"], None, ["BASICA", "MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-073", "Corrección hallazgos auditoría", 7,
        4.0, 2.0, 10, "mixto", ["WBS-072"], None, ["BASICA", "MEDIA", "ALTA"],
    ),

    # === FASE 8 — MANTENIMIENTO ===
    WBSTaskTemplate(
        "WBS-080", "Configuración retainer", 8,
        1.0, 2.0, 2, "plataforma", ["WBS-073"], None, ["MEDIA", "ALTA"],
    ),
    WBSTaskTemplate(
        "WBS-081", "Vigilancia continua (M8 continuo)", 8,
        0, 4.0, 0, "plataforma", ["WBS-080"], None, ["MEDIA", "ALTA"],
    ),
]


def get_tasks_for_categoria(categoria: str) -> list[WBSTaskTemplate]:
    cat = (categoria or "").strip().upper()
    return [t for t in WBS_CATALOG if cat in t.applies_to]
