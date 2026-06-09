"""WorkflowPhase enum · 10 fases lifecycle canonical (ADR-026 + SAN-C MB-11.1).

Supersedes:
- ADR-007 nomenclatura técnica 7 fases.
- ADR-026 v1 lifecycle 8 fases (FASE 8 plan v4.2 · pre-SAN-C).

SAN-C MB-11.1 · separa 2 sub-fases del manual ENS plan v4.2 que estaban
contenidas implícitamente en fases padre:

- ``analisis_riesgos`` separada de ``diagnostico`` (Manual fase 4 vs 3)
- ``dda_final`` separada de ``implantacion`` (Manual fase 7 vs 6)

Las 10 fases lifecycle cubren ciclo cliente completo (pre-venta → cierre):

    pre_venta        · proyecto creado, sin onboarding completo
    onboarding       · M16 sesión cliente activa (preguntas/respuestas)
    diagnostico      · M21 diagnosis_runs + maturity scoring
    analisis_riesgos · M02 MAGERIT analysis iniciado, sin aprobar (NEW MB-11.1)
    adecuacion       · M01 categorización + M02 MAGERIT analysis approved
    implantacion     · M03 DdA entries + M05/M06 controls + audit_checklist
    dda_final        · DdA todas implementadas, pre-verificación (NEW MB-11.1)
    verificacion     · M08 verification_runs + findings
    conformidad      · M09 audit_preparation + M27 conformity_submissions
    retainer_cierre  · M23 retainer_contracts + M25 lifecycle events

Persistencia: ``projects.fase`` VARCHAR(50) NOT NULL CHECK constraint
(migración ``workflow_phase_10_canonical``). Source of truth primaria
para get_current_phase con CASCADE fallback derivado en
workflow_state.py si fase desactualizada vs realidad motors.

Backward-compat: projects existentes con valores 8-fase originales siguen
válidos en CHECK constraint extendido (10 fases incluyen las 8
originales). Migration solo extiende constraint, no rewrites data.
"""
from __future__ import annotations

from enum import Enum


class WorkflowPhase(str, Enum):
    """10 fases lifecycle canonical (ADR-026 + SAN-C MB-11.1)."""

    PRE_VENTA = "pre_venta"
    ONBOARDING = "onboarding"
    DIAGNOSTICO = "diagnostico"
    ANALISIS_RIESGOS = "analisis_riesgos"  # NEW MB-11.1
    ADECUACION = "adecuacion"
    IMPLANTACION = "implantacion"
    DDA_FINAL = "dda_final"  # NEW MB-11.1
    VERIFICACION = "verificacion"
    CONFORMIDAD = "conformidad"
    RETAINER_CIERRE = "retainer_cierre"

    @classmethod
    def ordered(cls) -> list["WorkflowPhase"]:
        """Lista 10 fases en orden lifecycle (pre_venta → retainer_cierre)."""
        return [
            cls.PRE_VENTA,
            cls.ONBOARDING,
            cls.DIAGNOSTICO,
            cls.ANALISIS_RIESGOS,
            cls.ADECUACION,
            cls.IMPLANTACION,
            cls.DDA_FINAL,
            cls.VERIFICACION,
            cls.CONFORMIDAD,
            cls.RETAINER_CIERRE,
        ]

    def previous(self) -> "WorkflowPhase | None":
        """Fase anterior en orden lifecycle (None si pre_venta)."""
        ordered = self.ordered()
        idx = ordered.index(self)
        return ordered[idx - 1] if idx > 0 else None

    def next(self) -> "WorkflowPhase | None":
        """Fase siguiente en orden lifecycle (None si retainer_cierre)."""
        ordered = self.ordered()
        idx = ordered.index(self)
        return ordered[idx + 1] if idx < len(ordered) - 1 else None
