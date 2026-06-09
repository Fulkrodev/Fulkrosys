/**
 * PhaseStepper · stepper visual horizontal 8 fases lifecycle (FASE 8 · ADR-026).
 *
 * Wrapper sobre `Stepper` UI base (existing) con WorkflowPhase enum.
 * Reusa pattern Sesión 5.B (Stepper genérico).
 */
"use client";

import { Stepper } from "@/components/ui/stepper";
import {
  PHASE_LABELS,
  WORKFLOW_PHASES,
  type WorkflowPhase,
} from "@/lib/admin-workflow/schemas";

export interface PhaseStepperProps {
  currentPhase: WorkflowPhase;
  className?: string;
}

export function PhaseStepper({ currentPhase, className }: PhaseStepperProps) {
  const steps = WORKFLOW_PHASES.map((p) => ({
    id: p,
    label: PHASE_LABELS[p],
  }));
  const currentIndex = WORKFLOW_PHASES.indexOf(currentPhase);

  return (
    <Stepper steps={steps} currentIndex={currentIndex} className={className} />
  );
}
