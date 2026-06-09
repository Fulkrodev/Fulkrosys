"""MilestoneFactory · genera ContractMilestone desde MilestoneSpec
existing (MB-18.2 ADR-040).

Usa ``PricingCalculator.get_milestones(categoria, total)`` existing
(``backend/app/core/pricing/calculator.py:282``) que retorna
``MilestonePricing.milestones`` (list ``MilestoneBreakdown``: code +
pct + pct_display + description + amount).

Mapeo ``milestone_name → workflow_phase_index`` canónico per
WorkflowPhase enum (10 fases ADR-026 + SAN-C MB-11.1):
    0: PRE_VENTA
    1: ONBOARDING
    2: DIAGNOSTICO
    3: ANALISIS_RIESGOS
    4: ADECUACION
    5: IMPLANTACION
    6: DDA_FINAL
    7: VERIFICACION
    8: CONFORMIDAD
    9: RETAINER_CIERRE

Mapping aplicado:
- ``hito_1_firma`` → 1 ONBOARDING (firma del contrato disparador
  arranque proyecto)
- ``hito_2_dda_politicas`` → 4 ADECUACION (BASICA · DdA + políticas)
- ``hito_2_diagnostico_ar`` → 3 ANALISIS_RIESGOS (MEDIA/ALTA)
- ``hito_3_dda_politicas_alta`` → 4 ADECUACION (ALTA categoría)
- ``hito_3_dda_sgsi`` → 4 ADECUACION (MEDIA · DdA + SGSI)
- ``hito_3_dossier_entregado`` → 7 VERIFICACION (BASICA fin)
- ``hito_4_dossier_auditor`` → 7 VERIFICACION (MEDIA/ALTA)
- ``hito_5_certificacion`` → 8 CONFORMIDAD
- fallback (codes no listados) → 4 ADECUACION conservador (re-asignar
  via metadata override si emerge necesidad)

Idempotente: UNIQUE (contract_id, milestone_index) skip rows existing.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.pricing.calculator import (
    PricingCalculator,
    PricingError,
)
from backend.app.models.billing_milestones import ContractMilestone

logger = logging.getLogger(__name__)


# Mapping milestone code → workflow phase index canónico.
MILESTONE_PHASE_MAPPING: dict[str, int] = {
    "hito_1_firma": 1,             # ONBOARDING
    "hito_2_dda_politicas": 4,     # ADECUACION (BASICA)
    "hito_2_diagnostico_ar": 3,    # ANALISIS_RIESGOS (MEDIA/ALTA)
    "hito_3_dda_politicas_alta": 4,
    "hito_3_dda_sgsi": 4,          # ADECUACION (MEDIA)
    "hito_3_dossier_entregado": 7, # VERIFICACION (BASICA fin)
    "hito_4_dossier_auditor": 7,   # VERIFICACION (MEDIA/ALTA)
    "hito_5_certificacion": 8,     # CONFORMIDAD
}

DEFAULT_PHASE_FALLBACK = 4  # ADECUACION conservador

# #28 · duración estimada de implantación por categoría (semanas · midpoint de
# los rangos canónicos: BÁSICA 4-6 · MEDIA 8-10 · ALTA 12-16). Distribuye las
# fechas previstas de cobro a lo largo del proyecto.
TIER_DURATION_WEEKS: dict[str, int] = {"BASICA": 6, "MEDIA": 10, "ALTA": 16}


def estimate_scheduled_date(
    start_date: date, phase_index: int, categoria: str,
) -> date:
    """#28 · Fecha prevista de cobro de un hito: distribuye la duración del
    proyecto (por categoría) según la fase del hito (1=firma→inicio, 8=
    conformidad→fin). Estimación honesta · el admin puede ajustarla después."""
    weeks = TIER_DURATION_WEEKS.get((categoria or "").upper(), 10)
    frac = max(0.0, min(1.0, (phase_index - 1) / 7.0))
    return start_date + timedelta(weeks=round(weeks * frac))


class MilestoneFactoryError(Exception):
    """Error genérico MilestoneFactory."""


def resolve_workflow_phase(milestone_code: str) -> int:
    """Devuelve workflow_phase_index canónico para un milestone code.

    Fallback ``ADECUACION`` (4) si code no está en mapping · loggea
    warning para detectar codes nuevos sin mapping.
    """
    phase = MILESTONE_PHASE_MAPPING.get(milestone_code)
    if phase is None:
        logger.warning(
            "milestone code %r sin phase mapping · usando fallback %d "
            "(ADECUACION) · revisar MILESTONE_PHASE_MAPPING",
            milestone_code, DEFAULT_PHASE_FALLBACK,
        )
        return DEFAULT_PHASE_FALLBACK
    return phase


class MilestoneFactory:
    """Materializa ContractMilestone rows desde Contract + categoria.

    Idempotente: UNIQUE (contract_id, milestone_index) skip rows ya
    existentes. Permite re-invoke seguro tras edits contract amount
    o re-asignación categoría.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._calculator = PricingCalculator()

    async def create_milestones_for_contract(
        self,
        *,
        contract_id: UUID,
        project_id: UUID,
        categoria: str,
        contract_total: Decimal,
        billing_trigger: str = "phase_complete",
        vat_percent: Decimal = Decimal("21.00"),
        blocking_next_phase: bool = True,
        auto_billing_enabled: bool = True,
        start_date: date | None = None,
    ) -> list[ContractMilestone]:
        """Crea ContractMilestone records desde MilestoneSpec existing.

        Args:
            contract_id: FK Contract.
            project_id: FK Project.
            categoria: BASICA | MEDIA | ALTA.
            contract_total: importe total contrato.
            billing_trigger: default ``phase_complete``.
            vat_percent: default 21.
            blocking_next_phase: default True (workflow auto-advance
                tras paid).
            auto_billing_enabled: default True (auto-bill on phase
                complete).

        Returns:
            Lista de ContractMilestone creados (skip existing).
        """
        try:
            pricing = self._calculator.get_milestones(categoria, contract_total)
        except PricingError as exc:
            raise MilestoneFactoryError(
                f"Pricing inválido para categoria={categoria!r} "
                f"total={contract_total}: {exc}"
            ) from exc

        existing_indexes = await self._existing_milestone_indexes(contract_id)
        created: list[ContractMilestone] = []

        for index, breakdown in enumerate(pricing.milestones):
            if index in existing_indexes:
                logger.debug(
                    "milestone index=%d contract=%s ya existe · skip",
                    index, contract_id,
                )
                continue
            phase_index = resolve_workflow_phase(breakdown.code)
            milestone = ContractMilestone(
                contract_id=contract_id,
                project_id=project_id,
                milestone_index=index,
                milestone_name=breakdown.code,
                workflow_phase_index=phase_index,
                billing_trigger=billing_trigger,
                scheduled_date=(
                    estimate_scheduled_date(start_date, phase_index, categoria)
                    if start_date is not None else None
                ),
                amount_eur=breakdown.amount,
                vat_percent=vat_percent,
                percent_of_total=breakdown.pct_display,
                blocking_next_phase=blocking_next_phase,
                auto_billing_enabled=auto_billing_enabled,
                metadata_jsonb={
                    "description": breakdown.description,
                    "categoria": pricing.categoria,
                },
            )
            self.db.add(milestone)
            created.append(milestone)

        if created:
            await self.db.flush()
            for m in created:
                await self.db.refresh(m)

        logger.info(
            "MilestoneFactory contract=%s created=%d skipped=%d total_pricing=%s",
            contract_id, len(created),
            len(pricing.milestones) - len(created),
            pricing.contract_total,
        )
        return created

    async def _existing_milestone_indexes(
        self, contract_id: UUID,
    ) -> set[int]:
        result = await self.db.execute(
            select(ContractMilestone.milestone_index).where(
                ContractMilestone.contract_id == contract_id,
            )
        )
        return set(result.scalars().all())


__all__ = [
    "MilestoneFactory",
    "MilestoneFactoryError",
    "MILESTONE_PHASE_MAPPING",
    "DEFAULT_PHASE_FALLBACK",
    "resolve_workflow_phase",
]
