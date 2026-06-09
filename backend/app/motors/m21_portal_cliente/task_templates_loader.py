"""ClientTask templates loader (ADR-038 SAN-D MB-14.3 · EXPANDED 1.C.D.A v3.8).

Carga `task_templates.yaml` con templates · proporciona helpers
para filtrar templates aplicables a (categoria, archetype, phase) y
ahora también filter enriched 19-dims (1.C.D.A v3.8).

Loader patrón MB-15 magerit_libro_ii_loader · path absoluto via
``Path(__file__).parent``.

OPS-045 caso 5 sostenido (sub-atom 1.C.D.A v3.8): extend YAML existing
con campos enriched OPCIONALES backward-compat preservada. 18 templates
legacy continúan funcionando sin modificación · nuevos templates enriched
pueden usar campos extras (description_detailed_es · rationale_es · etc).

Sub-atom 1.D.G v3.11 (cross-actor dependencies): añadido `primary_actor`
opcional + derive helper + actor-aware enriched fields. Default heuristic
backward-compat (NO breaking change · field optional · derived si no set).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

# Sub-atom 1.D.G v3.11 · primary actor enum
PrimaryActor = Literal["admin", "cliente", "system"]


class ArchetypeVariant(BaseModel):
    """Variante de sub-paso per arquetipo · sobrepone fields canónicos.

    Permite que un sub-paso canónico tenga ajustes especí­ficos por
    archetype (extra focus · reference_norms adicionales · etc).
    """

    extra_focus: str | None = None
    reference_norms: list[str] = Field(default_factory=list)
    extra_actors: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class TaskTemplate(BaseModel):
    """Template canónico de tarea workflow · backward-compat enriched.

    Campos LEGACY (sub-atom plan v3.3) son required salvo opcionales antiguos.
    Campos ENRICHED (sub-atom 1.C.D.A v3.8) son TODOS opcionales · permiten
    extension progressive de templates sin romper los 18 legacy existing.
    """

    # ============= LEGACY (backward-compat) =============
    id: str
    phase: str
    applicable_categories: list[str] | str  # list o "ALL"
    applicable_archetypes: list[str] | str  # list o "ALL"
    title: str
    description: str | None = None
    cta_label: str | None = None
    cta_url: str | None = None
    expected_evidence_type: str | None = None
    expected_evidence_count: int = 1
    priority: int = 0
    estimated_days: int | None = None

    # ============= ENRICHED v3.8 (todos opcionales) =============
    order_within_phase: int | None = None
    """Posición secuencial dentro de la fase · drive timeline ordering."""

    applicable_size_ranges: list[str] | str | None = None
    """Subset Anexo L dim 3 · micro/pequeno/mediano/grande/enterprise · "ALL" o list."""

    applicable_madurez_min: str | None = None
    """L0..L5 · sub-paso aplica si proyecto.madurez_ens_actual >= min."""

    applicable_madurez_max: str | None = None
    """L0..L5 · sub-paso aplica si proyecto.madurez_ens_actual <= max."""

    requires_dora: bool = False
    """True · sólo aplica si project.aplica_dora != 'no'."""

    requires_dpo: bool = False
    """True · sólo aplica si project.dpo_designado != 'no_designado'."""

    requires_nis2: bool = False
    """True · sólo aplica si project.aplica_nis2 != 'no'."""

    requires_ai_act: bool = False
    """True · sólo aplica si project.aplica_ai_act != 'no'."""

    requires_datos_sensibles: bool = False
    """True · sólo aplica si project.procesa_datos_sensibles_rgpd9."""

    description_detailed_es: str | None = None
    """Texto hyper-explicativo · "qué hacer paso a paso" (Anexo M format)."""

    rationale_es: str | None = None
    """Por qué este paso ahora · ENS reference · business context."""

    deliverable_codes: list[str] = Field(default_factory=list)
    """Codes plantilla E-XXX que produce este sub-paso (E-040 · E-052 · etc)."""

    prerequisite_template_ids: list[str] = Field(default_factory=list)
    """IDs templates previos que deben completarse antes."""

    actors: list[str] = Field(default_factory=list)
    """Personas/roles involucrados (CISO · DPO · responsable_TI · etc)."""

    completion_criteria_detailed: list[str] = Field(default_factory=list)
    """Lista bullet de criterios completion · marca paso como done."""

    adaptation_notes_es: str | None = None
    """Notas de adaptación per envergadura · per archetype · etc."""

    tooltips_ens: dict[str, str] = Field(default_factory=dict)
    """Mapping ENS-control-code → tooltip explicativo (op.acc.5 · mp.s.* · etc)."""

    archetype_variants: dict[str, ArchetypeVariant] = Field(default_factory=dict)
    """Mapping archetype → ArchetypeVariant · sobrepone fields canónicos."""

    is_enriched: bool = False
    """Marcador · True si template usa enriched fields (helper UX)."""

    # ============= 1.D.G v3.11 CROSS-ACTOR DEPENDENCIES =============
    primary_actor: PrimaryActor | None = None
    """Quien debe avanzar el step desde estado actual (admin · cliente · system).

    Si None · se deriva via `derive_primary_actor(actors)` heuristica:
    - "system" si actors solo agentes A##_* prefix
    - "admin" si first non-agent actor == "Marcos" o lista vacía
    - "cliente" si first non-agent actor != "Marcos" (cliente_PoC · RSEG_cliente · etc)
    """

    estimated_days_to_complete: int | None = None
    """Override estimated_days specific para "Marcos prepara · estará listo en X días" UI cliente."""

    notify_on_unblock: bool = True
    """Si True dispatcha notification cliente/admin cuando step pasa de blocked → available."""

    notification_template_cliente: str | None = None
    """Plantilla R29 friendly cuando cliente recibe unblock notification.

    Format: "Marcos terminó {step_title} · te toca a ti"
    """

    notification_template_admin: str | None = None
    """Plantilla útil cuando Marcos recibe unblock notification.

    Format: "{cliente_name} completó {step_title} · puedes proceder"
    """

    model_config = ConfigDict(extra="forbid")


class TaskTemplatesCatalog(BaseModel):
    version: str
    templates: list[TaskTemplate]


@lru_cache(maxsize=1)
def load_task_templates() -> TaskTemplatesCatalog:
    """Carga yaml templates · lru_cache singleton."""
    yaml_path = Path(__file__).parent / "task_templates.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TaskTemplatesCatalog(**data)


def reload_task_templates() -> TaskTemplatesCatalog:
    """Reset cache · útil para tests."""
    load_task_templates.cache_clear()
    return load_task_templates()


def get_templates_for_phase(
    phase: str,
    categoria: str,
    archetype: Optional[str] = None,
) -> list[TaskTemplate]:
    """Filtra templates aplicables a (phase, categoria, archetype) · LEGACY filter.

    Reglas (backward-compat):
    - phase exact match
    - applicable_categories "ALL" o categoria in list
    - applicable_archetypes "ALL" o archetype in list (None archetype
      treated as "ALL"-passing)
    """
    catalog = load_task_templates()
    result = []
    for tmpl in catalog.templates:
        if tmpl.phase != phase:
            continue
        cats = tmpl.applicable_categories
        if cats != "ALL" and categoria not in cats:
            continue
        archs = tmpl.applicable_archetypes
        if archs != "ALL":
            if archetype is None or archetype not in archs:
                continue
        result.append(tmpl)
    return result


def get_template_by_id(template_id: str) -> Optional[TaskTemplate]:
    catalog = load_task_templates()
    return next(
        (t for t in catalog.templates if t.id == template_id), None,
    )


# ============= 1.D.G v3.11 CROSS-ACTOR HELPERS =============


def _is_agent_id(actor: str) -> bool:
    """A##_xxx pattern (A11_auditor_virtual · A21_discrepancias · etc)."""
    return (
        len(actor) >= 3
        and actor[0] == "A"
        and actor[1:3].isdigit()
    )


def derive_primary_actor(actors: list[str]) -> PrimaryActor:
    """Deriva quien debe avanzar el step desde actors list.

    Reglas:
    - actors vacío → "admin" (default safe · Marcos drive)
    - actors solo A##_* agentes → "system"
    - first non-agent == "Marcos" → "admin"
    - first non-agent != "Marcos" → "cliente"
    """
    if not actors:
        return "admin"
    non_agent = [a for a in actors if not _is_agent_id(a)]
    if not non_agent:
        return "system"
    first = non_agent[0]
    if first == "Marcos":
        return "admin"
    return "cliente"


def resolve_primary_actor(template: TaskTemplate) -> PrimaryActor:
    """Returns primary_actor explícito · fallback derive desde actors."""
    if template.primary_actor is not None:
        return template.primary_actor
    return derive_primary_actor(template.actors)


# ============= ENRICHED filter 1.C.D.A v3.8 =============


_MADUREZ_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}


def _matches_size_range(
    template: TaskTemplate, project_tamano: str | None,
) -> bool:
    """Sub-paso aplica si applicable_size_ranges = None/ALL o project_tamano in list."""
    ranges = template.applicable_size_ranges
    if ranges is None or ranges == "ALL":
        return True
    if project_tamano is None:
        return False
    return project_tamano in ranges


def _matches_madurez_range(
    template: TaskTemplate, project_madurez: str | None,
) -> bool:
    """Sub-paso aplica si madurez_ens_actual está entre min/max (si declarados)."""
    if not template.applicable_madurez_min and not template.applicable_madurez_max:
        return True
    if project_madurez is None:
        return True
    p_level = _MADUREZ_ORDER.get(project_madurez)
    if p_level is None:
        return True
    if template.applicable_madurez_min:
        min_lvl = _MADUREZ_ORDER.get(template.applicable_madurez_min, 0)
        if p_level < min_lvl:
            return False
    if template.applicable_madurez_max:
        max_lvl = _MADUREZ_ORDER.get(template.applicable_madurez_max, 5)
        if p_level > max_lvl:
            return False
    return True


def _matches_legal_requirements(
    template: TaskTemplate, project_dims: dict[str, Any],
) -> bool:
    """requires_* flags · sub-paso aplica si flag legal cliente match."""
    if template.requires_dora and project_dims.get("aplica_dora", "no") == "no":
        return False
    if template.requires_dpo and project_dims.get("dpo_designado", "no_designado") == "no_designado":
        return False
    if template.requires_nis2 and project_dims.get("aplica_nis2", "no") == "no":
        return False
    if template.requires_ai_act and project_dims.get("aplica_ai_act", "no") == "no":
        return False
    if template.requires_datos_sensibles and not project_dims.get(
        "procesa_datos_sensibles_rgpd9", False,
    ):
        return False
    return True


def get_enriched_steps_for_project(
    project_dims: dict[str, Any],
    phase_filter: str | None = None,
) -> list[TaskTemplate]:
    """Filtra templates aplicables al proyecto según 19 dimensiones (Anexo L v3.8).

    Args:
        project_dims: dict con dimensions del project (categoria_objetivo ·
            archetype · tamano_empleados · madurez_ens_actual · aplica_dora ·
            dpo_designado · aplica_nis2 · aplica_ai_act ·
            procesa_datos_sensibles_rgpd9 · fase · etc)
        phase_filter: si provided · filtrar solo phase match

    Returns:
        list[TaskTemplate] ordenada por phase + order_within_phase + priority
    """
    catalog = load_task_templates()
    categoria = (project_dims.get("categoria_objetivo") or "BASICA").upper()
    archetype = project_dims.get("archetype")
    tamano = project_dims.get("tamano_empleados")
    madurez = project_dims.get("madurez_ens_actual")

    result: list[TaskTemplate] = []
    for tmpl in catalog.templates:
        # Phase filter (opcional)
        if phase_filter is not None and tmpl.phase != phase_filter:
            continue
        # Legacy categorias filter
        cats = tmpl.applicable_categories
        if cats != "ALL" and categoria not in cats:
            continue
        # Legacy archetypes filter
        archs = tmpl.applicable_archetypes
        if archs != "ALL":
            if archetype is None or archetype not in archs:
                continue
        # Enriched size_range filter
        if not _matches_size_range(tmpl, tamano):
            continue
        # Enriched madurez range filter
        if not _matches_madurez_range(tmpl, madurez):
            continue
        # Enriched legal requirements (DORA · DPO · NIS2 · AI Act · datos sensibles)
        if not _matches_legal_requirements(tmpl, project_dims):
            continue
        result.append(tmpl)

    # Ordenar por (phase canonical order · order_within_phase · priority desc · id)
    from backend.app.core.workflow_phase import WorkflowPhase

    try:
        phase_order = {p.value: i for i, p in enumerate(WorkflowPhase.ordered())}
    except Exception:
        phase_order = {}

    def sort_key(t: TaskTemplate) -> tuple:
        return (
            phase_order.get(t.phase, 999),
            t.order_within_phase if t.order_within_phase is not None else 999,
            -t.priority,
            t.id,
        )

    result.sort(key=sort_key)
    return result


def apply_archetype_variant(
    template: TaskTemplate, archetype: str | None,
) -> dict[str, Any]:
    """Aplica archetype_variant si existe match · returns enriched dict.

    Returns mismo template dict con extra_focus/reference_norms/extra_actors
    aplicados desde variant si match arquetipo.
    """
    base = template.model_dump()
    if archetype is None:
        return base
    variant = template.archetype_variants.get(archetype)
    if variant is None:
        return base

    base["_variant_extra_focus"] = variant.extra_focus
    if variant.reference_norms:
        base["_variant_reference_norms"] = variant.reference_norms
    if variant.extra_actors:
        # Append a actors existing
        merged_actors = list(base.get("actors", [])) + list(variant.extra_actors)
        base["actors"] = list(dict.fromkeys(merged_actors))  # dedup preserve order

    return base
