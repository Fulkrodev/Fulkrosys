"""Motor 5 -- Obligations -- description personalisation.

Two rendering modes:
  1. Deterministic Jinja2 substitution (fast, no API call).
  2. LLM enrichment (adapts tone to client sector; fail-soft).
"""
from __future__ import annotations

import logging

from jinja2 import Environment, Undefined

from backend.app.motors.m05_obligations.instantiation_types import (
    ProjectContext,
)
from backend.app.motors.m05_obligations.types import ObligationTemplate

logger = logging.getLogger(__name__)

# Lenient Jinja2 environment: missing variables render as empty string.
# nosec B701 · renderiza TEXTO de obligaciones ENS (no HTML) · autoescape=True
# corromperia el texto (& -> &amp;) · datos de proyecto semi-confiables.
_jinja_env = Environment(undefined=Undefined)  # nosec B701


def _build_render_context(ctx: ProjectContext) -> dict:
    """Build a flat dict for Jinja2 template rendering.

    Templates use patterns like ``{{cliente.razon_social}}``,
    ``{{proyecto.nombre}}``, so we nest under those keys.
    """
    return {
        "cliente": {
            "razon_social": ctx.cliente.razon_social or "",
            "cif": ctx.cliente.cif or "",
            "sector": ctx.cliente.sector or "",
            "organo_aprobador_politicas": (
                ctx.cliente.organo_aprobador_politicas or ""
            ),
            "contacto_email": ctx.cliente.contacto_email or "",
        },
        "proyecto": {
            "nombre": ctx.nombre_proyecto or "",
            "categoria_ens": ctx.categoria_ens or "",
            "sistema_principal": ctx.sistema_principal or "",
            "fecha_kickoff": ctx.fecha_kickoff_iso or "",
        },
    }


def render_description_deterministic(
    template: ObligationTemplate,
    context: ProjectContext,
) -> str:
    """Render the template description with Jinja2 substitution.

    Uses lenient ``Undefined`` so missing variables silently become
    empty strings rather than raising errors.
    """
    raw = template.descripcion
    try:
        jinja_tpl = _jinja_env.from_string(raw)
        rendered = jinja_tpl.render(_build_render_context(context))
        return rendered
    except Exception:
        logger.warning(
            "Jinja2 render failed for template %s, returning raw",
            template.id,
            exc_info=True,
        )
        return raw


def enrich_description_with_llm(
    base_description: str,
    template: ObligationTemplate,
    context: ProjectContext,
) -> str:
    """Call LLM to adapt the description tone to the client sector.

    Fail-soft: returns *base_description* on any error so the pipeline
    never blocks on an LLM outage.
    """
    from backend.app.core.ai.llm_router import get_default_llm_router

    sector = context.cliente.sector or "general"

    prompt = (
        f"Eres un consultor ENS experto. Adapta la siguiente descripcion de "
        f"obligacion al sector '{sector}' del cliente '{context.cliente.razon_social}'. "
        f"Manten el significado tecnico y normativo intacto. No inventes requisitos. "
        f"Responde SOLO con la descripcion adaptada, sin explicaciones.\n\n"
        f"Descripcion original:\n{base_description}"
    )

    try:
        router = get_default_llm_router()
        response = router.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2,  # R3: LLM temp ≤ 0.2 (Ejecutable 8 Pasada 16 · F-13-04)
        )
        enriched = response.content.strip()
        if len(enriched) < 20:
            logger.warning(
                "LLM response too short for %s, using base description",
                template.id,
            )
            return base_description
        return enriched
    except Exception:
        logger.warning(
            "LLM enrichment failed for %s, using base description",
            template.id,
            exc_info=True,
        )
        return base_description
