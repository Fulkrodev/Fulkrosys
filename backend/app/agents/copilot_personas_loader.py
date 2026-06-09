"""Copilot personas loader · sub-atom 1.D.B.0.1 v3.10.

Carga + valida `docs/catalogs/copilot_personas_v1.yaml` (Anexo M v3.10).

Pattern consistent con M04 catalog_loader.py · M19 catalog_loader.py · M07
catalog_loader.py · sostener convention canonical FULKRO.

2 personas materialize Anexo M plan v3.10:
- `cliente` · tutor paciente R29 sostener · NO presión coercitiva
- `admin` · tutor cronológico R30 sostener · asume cero ENS Marcos

Cada persona expone:
- identity · tone · scope_boundaries_allowed/forbidden
- model_recommended · temperature · max_tokens · enable_prompt_caching
- proactive_triggers · system_prompt_template (Jinja-style placeholders)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "catalogs" /
    "copilot_personas_v1.yaml"
)


class CopilotPersonasLoadError(Exception):
    """Raised when copilot_personas YAML missing or invalid."""


# ════════════════════════════════════════════════════════════════════
# Pydantic schemas (validate YAML structure · type-safe access)
# ════════════════════════════════════════════════════════════════════


PersonaRole = Literal["cliente", "admin"]


class ScreenReference(BaseModel):
    """Referencia screen project-scoped · 1.D.F.0.D context-aware admin.

    Catalog entries used cuando Marcos pregunta "¿qué hago aquí?" y copiloto
    referencia botones específicos de la pantalla activa. Sostiene R30
    sostener (tutor cronológico · monkey-pilot friendly · button-level concreto).
    """

    model_config = ConfigDict(frozen=True)

    screen: str  # pattern path con [id] placeholder (e.g. "/admin/projects/[id]/dda")
    screen_name: str
    motor: str
    actions: list[str]
    context_hints: str


class CopilotPersona(BaseModel):
    """Definición persona individual cliente o admin."""

    model_config = ConfigDict(frozen=True)

    identity: str
    tone: list[str]
    scope_boundaries_allowed: list[str]
    scope_boundaries_forbidden: list[str]
    citations_required: bool
    model_recommended: str
    temperature: float = Field(ge=0.0, le=1.0)
    max_tokens: int = Field(ge=100, le=8000)
    enable_prompt_caching: bool
    proactive_triggers: list[str]
    system_prompt_template: str
    # 1.D.F.0.D · screen catalog opcional (solo admin · cliente persona omite)
    screen_references_catalog: list[ScreenReference] = Field(
        default_factory=list,
    )


class CopilotPersonasMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    created: str
    subatom: str
    plan_version: str
    anexo_reference: str


class CopilotPersonasCatalog(BaseModel):
    """Root structure copilot_personas YAML."""

    model_config = ConfigDict(frozen=True)
    version: str
    metadata: CopilotPersonasMetadata
    personas: dict[str, CopilotPersona]


# ════════════════════════════════════════════════════════════════════
# Loader
# ════════════════════════════════════════════════════════════════════


_CACHED_CATALOG: CopilotPersonasCatalog | None = None


def load_catalog(
    catalog_path: Path | None = None, *, use_cache: bool = True,
) -> CopilotPersonasCatalog:
    """Carga + valida YAML personas.

    `use_cache=True` cachea singleton catalog en memoria (catalog estable
    durante runtime · NO hot-reload). Tests pueden pasar `use_cache=False`
    para refresh.
    """
    global _CACHED_CATALOG
    if use_cache and _CACHED_CATALOG is not None and catalog_path is None:
        return _CACHED_CATALOG

    path = catalog_path or CATALOG_PATH
    if not path.exists():
        raise CopilotPersonasLoadError(f"Catalog not found at {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise CopilotPersonasLoadError(f"YAML parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise CopilotPersonasLoadError("Catalog root is not a dict")

    try:
        catalog = CopilotPersonasCatalog.model_validate(data)
    except Exception as exc:
        raise CopilotPersonasLoadError(
            f"Catalog schema validation failed: {exc}",
        ) from exc

    # Sanity check personas required (cliente · admin)
    required_roles = {"cliente", "admin"}
    missing = required_roles - set(catalog.personas.keys())
    if missing:
        raise CopilotPersonasLoadError(
            f"Missing required personas: {sorted(missing)}",
        )

    if use_cache and catalog_path is None:
        _CACHED_CATALOG = catalog
    return catalog


def get_persona(role: PersonaRole) -> CopilotPersona:
    """Lookup persona by role · raises if role inválido."""
    catalog = load_catalog()
    persona = catalog.personas.get(role)
    if persona is None:
        raise CopilotPersonasLoadError(
            f"Persona role '{role}' not found in catalog",
        )
    return persona


def build_system_prompt(
    persona: CopilotPersona, context: dict[str, Any],
) -> str:
    """Render system_prompt_template with context placeholders.

    Uses str.format · simple placeholder substitution. Missing keys
    fallback to "(no disponible)" string para evitar KeyError en runtime.

    Context expected keys:
    - cliente persona: client_company · project_category · project_context · current_step_context
    - admin persona: portfolio_context · active_client_context
      · current_screen_context (1.D.F.0.D) · current_screen_actions (1.D.F.0.D)
    """
    template = persona.system_prompt_template
    safe_context: dict[str, Any] = {}
    # Build safe defaults for known placeholders
    placeholder_defaults = {
        "client_company": "(empresa cliente)",
        "project_category": "(categoría ENS)",
        "project_context": "(contexto proyecto no disponible)",
        "current_step_context": "(step actual no disponible)",
        "portfolio_context": "(portfolio no disponible)",
        "active_client_context": "(cliente activo no disponible)",
        # 1.D.F.0.D · screen-aware placeholders (admin persona)
        "current_screen_context": "(sin pantalla activa identificada)",
        "current_screen_actions": "(sin acciones específicas · da guidance conceptual general)",
    }
    safe_context.update(placeholder_defaults)
    safe_context.update(
        {k: v for k, v in context.items() if v is not None},
    )

    try:
        return template.format(**safe_context)
    except KeyError as exc:
        raise CopilotPersonasLoadError(
            f"Template placeholder missing: {exc} · template needs more "
            "context keys o update placeholder_defaults",
        ) from exc


def normalize_screen_pattern(screen_path: str) -> str:
    """Normaliza pathname con UUID/id → pattern catálogo con [id].

    Ej:
      "/admin/projects/abc-uuid-123/dda" → "/admin/projects/[id]/dda"
      "/admin/projects/abc/mcps" → "/admin/projects/[id]/mcps"
      "/admin/workflow-command-center/projects/uuid/" → "/admin/workflow-command-center/projects/[id]"

    Returns pathname original si no matchea project-scoped pattern (NO normalize).
    """
    import re

    # Limpieza común: quita query (?...) y fragmento (#...) · las rutas del
    # catálogo son pathnames puros (cliente /client-portal/* y admin).
    screen_path = (screen_path or "").split("?", 1)[0].split("#", 1)[0]

    # Pattern admin project-scoped: /admin/projects/{id}/* o
    # /admin/workflow-command-center/projects/{id}/*
    patterns = (
        (
            r"^(/admin/projects/)([^/]+)(/[^?]*)?",
            lambda m: f"{m.group(1)}[id]{m.group(3) or ''}",
        ),
        (
            r"^(/admin/workflow-command-center/projects/)([^/]+)(/[^?]*)?",
            lambda m: f"{m.group(1)}[id]{m.group(3) or ''}",
        ),
    )

    for pattern, replacer in patterns:
        match = re.match(pattern, screen_path)
        if match:
            normalized = replacer(match)
            # Trim trailing slash si presente (catalog pattern stable form)
            if normalized.endswith("/") and len(normalized) > 1:
                normalized = normalized[:-1]
            return normalized

    # Rutas no project-scoped (cliente /client-portal/*, admin top-level):
    # normaliza barra final para que el match exacto del catálogo no falle
    # (p.ej. "/client-portal/" → "/client-portal", "/client-portal/dda/" → …/dda).
    if screen_path.endswith("/") and len(screen_path) > 1:
        screen_path = screen_path[:-1]
    return screen_path


def lookup_screen_reference(
    persona: CopilotPersona, screen_path: str | None,
) -> ScreenReference | None:
    """Lookup screen reference en catalog · normalize pathname antes match.

    Returns None si screen_path None o no match en catalog · upstream service
    debe fallback safe defaults ("sin pantalla activa identificada").
    """
    if not screen_path or not persona.screen_references_catalog:
        return None
    normalized = normalize_screen_pattern(screen_path)
    for entry in persona.screen_references_catalog:
        if entry.screen == normalized:
            return entry
    return None
