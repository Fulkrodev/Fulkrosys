"use client";

/**
 * MilestoneTimeline · 8 hitos workflow ENS visualizados (SAN-E v3.MB-3.2).
 *
 * Hitos contractuales tipicos proyecto ALTA mapeados a glosario ENS:
 * 1. Onboarding · 2. Diagnostico · 3. MAGERIT · 4. Adecuacion ·
 * 5. Implantacion · 6. Verificacion · 7. Conformidad · 8. Retainer/Cierre
 *
 * #45 E0 · Status derivado de current_phase_index (ordinal canónico de
 * projects.fase) del backend M15 financial-summary. Fases < actual = completadas,
 * la actual = activa, posteriores = futuras. (Antes usaba milestone_index, el
 * índice secuencial del hito · NO la fase · y pintaba la fase equivocada.)
 *
 * Responsive: horizontal desktop · vertical stack mobile.
 */
import * as React from "react";
import { CheckCircle2, Circle, Clock } from "lucide-react";

import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";
import type { GlossaryKey } from "@/lib/glosario-ens";

interface PhaseDef {
  index: number;
  label: string;
  termKey: GlossaryKey;
}

// #45 E0 · 10 fases canónicas (WorkflowPhase.ordered · ordinal 0-based) para que
// el índice coincida 1:1 con current_phase_index. El bug previo usaba un array de
// 8 fases manejado por milestone_index (secuencial del hito · otra cosa).
const PHASES: PhaseDef[] = [
  { index: 0, label: "Pre-venta", termKey: "workflow_pre_venta" },
  { index: 1, label: "Onboarding", termKey: "workflow_onboarding" },
  { index: 2, label: "Diagnóstico", termKey: "workflow_diagnostico" },
  { index: 3, label: "Análisis riesgos", termKey: "workflow_analisis_riesgos" },
  { index: 4, label: "Adecuación", termKey: "workflow_adecuacion" },
  { index: 5, label: "Implantación", termKey: "workflow_implantacion" },
  { index: 6, label: "DdA final", termKey: "workflow_dda_final" },
  { index: 7, label: "Verificación", termKey: "workflow_verificacion" },
  { index: 8, label: "Conformidad", termKey: "workflow_conformidad" },
  { index: 9, label: "Retainer / Cierre", termKey: "workflow_retainer_cierre" },
];

type PhaseStatus = "completed" | "active" | "upcoming";

function statusFor(phaseIndex: number, currentIndex: number | null): PhaseStatus {
  if (currentIndex === null || currentIndex === undefined) return "upcoming";
  if (phaseIndex < currentIndex) return "completed";
  if (phaseIndex === currentIndex) return "active";
  return "upcoming";
}

interface PhaseNodeProps {
  phase: PhaseDef;
  status: PhaseStatus;
}

function PhaseNode({ phase, status }: PhaseNodeProps) {
  const dotColor = {
    completed: "bg-fulkro-success border-fulkro-success text-white",
    active: "bg-fulkro-warning/20 border-fulkro-warning text-fulkro-warning animate-pulse",
    upcoming: "bg-white border-fulkro-ink-200 text-fulkro-ink-600",
  }[status];

  const labelColor = {
    completed: "text-[color:var(--fulkro-title)]",
    active: "text-fulkro-warning font-bold",
    upcoming: "text-fulkro-ink-600",
  }[status];

  const Icon = status === "completed" ? CheckCircle2 : status === "active" ? Clock : Circle;

  return (
    <div className="flex min-w-[100px] flex-col items-center gap-2">
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-full border-2 transition-colors",
          dotColor,
        )}
      >
        <Icon size={16} strokeWidth={2.4} />
      </div>
      <div className="flex flex-col items-center gap-0.5 text-center">
        <span className={cn("text-xs font-medium", labelColor)}>
          {phase.label}
        </span>
        <TooltipENS term={phase.termKey} iconSize={11} />
      </div>
    </div>
  );
}

export interface MilestoneTimelineProps {
  currentPhaseIndex: number | null;
}

export function MilestoneTimeline({
  currentPhaseIndex,
}: MilestoneTimelineProps) {
  return (
    <div className="rounded-lg border border-fulkro-ink-200 bg-white p-6">
      <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-[color:var(--fulkro-title)]">
        Hitos del contrato
      </h3>

      {/* Desktop horizontal */}
      <div className="hidden md:block">
        <div className="relative flex items-start justify-between">
          {/* Línea connector base */}
          <div className="absolute left-[18px] right-[18px] top-[18px] h-0.5 bg-fulkro-ink-200" />
          {/* Línea progress · width derivada de currentIndex */}
          {currentPhaseIndex !== null && currentPhaseIndex > 0 ? (
            <div
              className="absolute left-[18px] top-[18px] h-0.5 bg-fulkro-success transition-all"
              style={{
                width: `calc(${
                  currentPhaseIndex / Math.max(1, PHASES.length - 1)
                } * (100% - 36px))`,
              }}
            />
          ) : null}
          {PHASES.map((phase) => (
            <PhaseNode
              key={phase.index}
              phase={phase}
              status={statusFor(phase.index, currentPhaseIndex)}
            />
          ))}
        </div>
      </div>

      {/* Mobile vertical stack */}
      <div className="flex flex-col gap-4 md:hidden">
        {PHASES.map((phase, idx) => {
          const status = statusFor(phase.index, currentPhaseIndex);
          const isLast = idx === PHASES.length - 1;
          return (
            <div key={phase.index} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border-2",
                    {
                      completed:
                        "bg-fulkro-success border-fulkro-success text-white",
                      active:
                        "bg-fulkro-warning/20 border-fulkro-warning text-fulkro-warning",
                      upcoming:
                        "bg-white border-fulkro-ink-200 text-fulkro-ink-600",
                    }[status],
                  )}
                >
                  {status === "completed" ? (
                    <CheckCircle2 size={14} strokeWidth={2.4} />
                  ) : status === "active" ? (
                    <Clock size={14} strokeWidth={2.4} />
                  ) : (
                    <Circle size={14} strokeWidth={2.4} />
                  )}
                </div>
                {isLast ? null : (
                  <div
                    className={cn(
                      "mt-1 w-0.5 flex-1",
                      status === "completed"
                        ? "bg-fulkro-success"
                        : "bg-fulkro-ink-200",
                    )}
                  />
                )}
              </div>
              <div className="flex flex-1 items-center gap-2 pb-3">
                <span
                  className={cn(
                    "text-sm",
                    status === "active"
                      ? "font-bold text-fulkro-warning"
                      : status === "completed"
                      ? "text-[color:var(--fulkro-title)]"
                      : "text-fulkro-ink-600",
                  )}
                >
                  {phase.label}
                </span>
                <TooltipENS term={phase.termKey} iconSize={12} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
