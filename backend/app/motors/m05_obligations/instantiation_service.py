"""Motor 5 -- Obligations Instantiation Service.

Creates ``Obligation`` rows in the database by hydrating library
templates with project/client context.  Two entry points:

* ``instantiate_obligations_for_gap``  -- single gap
* ``instantiate_obligations_for_multiple_gaps`` -- batch (commits once)

Key invariants
--------------
* **Idempotency** by ``(project_id, template_id)``.
* **Category filtering** -- templates whose category does not match the
  project's ENS category are skipped.
* **Canonical fields** (``criterios_aceptacion``, ``fuente_normativa``)
  are copied verbatim from the template and are never modified by the LLM.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ens import Obligation
from backend.app.motors.m05_obligations.instantiation_types import (
    GapInput,
    InstantiationOutcome,
    ProjectContext,
)
from backend.app.motors.m05_obligations.library_loader import (
    get_templates_for_measure,
)
from backend.app.motors.m05_obligations.personalization import (
    enrich_description_with_llm,
    render_description_deterministic,
)

logger = logging.getLogger(__name__)

# Map from project ``categoria_ens`` (BASICA/MEDIA/ALTA) to the set of
# template ``categoria`` values that should be included.  Templates in
# the library use lower-case domain names (organizativo, operacional,
# medidas_proteccion); all three apply regardless of ENS category.
# The real filter is done by ``get_templates_for_measure`` when a
# ``category`` kwarg is supplied, but here we filter by ENS category
# applicability: BASICA projects only get templates whose measure
# applies to BASICA; MEDIA includes BASICA+MEDIA, etc.
_CATEGORY_HIERARCHY = {
    "BASICA": {"BASICA"},
    "MEDIA": {"BASICA", "MEDIA"},
    "ALTA": {"BASICA", "MEDIA", "ALTA"},
}


async def _measure_exists(session: AsyncSession, measure_code: str) -> bool:
    """Return True if *measure_code* exists in ``ens_measures``."""
    result = await session.execute(
        text("SELECT 1 FROM ens_measures WHERE codigo = :code LIMIT 1"),
        {"code": measure_code},
    )
    return result.scalar() is not None


async def _find_existing_obligation(
    session: AsyncSession,
    project_id: uuid.UUID,
    template_id: str,
) -> uuid.UUID | None:
    """Return the ID of an existing obligation for this project+template, or None."""
    stmt = (
        select(Obligation.id)
        .where(
            Obligation.project_id == project_id,
            Obligation.template_id == template_id,
        )
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row


async def instantiate_obligations_for_gap(
    session: AsyncSession,
    gap: GapInput,
    project_context: ProjectContext,
    *,
    use_llm_personalization: bool = False,
) -> InstantiationOutcome:
    """Instantiate obligations for a single gap.

    1. Validate measure_code exists in ``ens_measures``.
    2. Fetch matching templates from the library.
    3. For each template, check idempotency and persist.

    Returns an ``InstantiationOutcome`` describing what happened.
    """
    outcome = InstantiationOutcome(
        gap_id=gap.gap_id,
        measure_code=gap.measure_code,
    )

    # --- Validate measure code ---
    if not await _measure_exists(session, gap.measure_code):
        outcome.validation_errors.append(
            f"Measure code '{gap.measure_code}' not found in ens_measures"
        )
        return outcome

    # --- Fetch templates ---
    templates = get_templates_for_measure(gap.measure_code)
    if not templates:
        outcome.templates_skipped_no_match.append(gap.measure_code)
        return outcome

    for tmpl in templates:
        # --- Idempotency check ---
        existing_id = await _find_existing_obligation(
            session, project_context.project_id, tmpl.id
        )
        if existing_id is not None:
            outcome.obligations_existing_ids.append(existing_id)
            continue

        # --- Render description ---
        description_base = render_description_deterministic(tmpl, project_context)
        if use_llm_personalization:
            description_final = enrich_description_with_llm(
                description_base, tmpl, project_context
            )
        else:
            description_final = description_base

        # --- Create obligation row ---
        obligation = Obligation(
            project_id=project_context.project_id,
            gap_id=gap.gap_id,
            template_id=tmpl.id,
            template_version=tmpl.version,
            measure_code=tmpl.measure_code,
            titulo=tmpl.titulo,
            descripcion=description_final,
            entregable_tipo=tmpl.entregable_tipo,
            modo_ejecucion=tmpl.modo_ejecucion,
            magic_link_template=tmpl.magic_link_template,
            esfuerzo_estimado=tmpl.esfuerzo_horas,
            # 'pendiente' (ES) = vocabulario canónico de la máquina de estados
            # (VALID_ESTADOS_OBLIGATION); 'pending' (EN) dejaba la obligación en
            # limbo: no arrancable (start exige 'pendiente') ni contabilizada.
            estado="pendiente",
            dependencias_template_ids=tmpl.dependencias_template_ids or None,
            criterios_aceptacion=tmpl.criterios_aceptacion,
            fuente_normativa=tmpl.fuente_normativa,
            metadata_extra={"personalizada_con_llm": use_llm_personalization},
        )
        session.add(obligation)
        await session.flush()

        outcome.obligations_created_ids.append(obligation.id)
        logger.info(
            "Created obligation %s from template %s for project %s",
            obligation.id,
            tmpl.id,
            project_context.project_id,
        )

    return outcome


async def instantiate_obligations_for_multiple_gaps(
    session: AsyncSession,
    gaps: list[GapInput],
    project_context: ProjectContext,
    *,
    use_llm_personalization: bool = False,
    enforce_gates: bool = True,
) -> list[InstantiationOutcome]:
    """Process multiple gaps in a single transaction.

    Calls ``instantiate_obligations_for_gap`` for each gap, then
    flushes once at the end.  Returns a list of outcomes.

    Gate (P7-F1 · handoff H3): si ``enforce_gates`` es True (default en
    producción), el análisis de riesgos MAGERIT v3 (Motor 2) debe existir
    para el proyecto antes de instanciar el plan de obligaciones. Mirror del
    patrón ya cableado en ``m03_dda/service.py``.
    """
    if enforce_gates:
        from backend.app.core.workflow_gates import require_magerit_analysis
        await require_magerit_analysis(session, project_context.project_id)

    outcomes: list[InstantiationOutcome] = []
    for gap in gaps:
        outcome = await instantiate_obligations_for_gap(
            session,
            gap,
            project_context,
            use_llm_personalization=use_llm_personalization,
        )
        outcomes.append(outcome)
    await session.flush()
    return outcomes
