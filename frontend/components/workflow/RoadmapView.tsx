/**
 * RoadmapView · vista timeline 8 fases lifecycle (FASE 8 · ADR-026).
 *
 * Layout: PhaseStepper top + grid PhaseCards 8 fases (responsive
 * 1col mobile / 2cols tablet / 4cols desktop).
 */
"use client";

import { PhaseCard } from "./PhaseCard";
import { PhaseStepper } from "./PhaseStepper";
import type { PhaseRoadmapEntry, WorkflowRoadmap } from "@/lib/admin-workflow/schemas";

export interface RoadmapViewProps {
  roadmap: WorkflowRoadmap;
  onPhaseClick?: (phase: PhaseRoadmapEntry) => void;
  className?: string;
}

export function RoadmapView({ roadmap, onPhaseClick, className }: RoadmapViewProps) {
  return (
    <div className={className}>
      <PhaseStepper currentPhase={roadmap.current_phase} className="mb-6" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {roadmap.phases.map((entry) => (
          <PhaseCard
            key={entry.phase}
            entry={entry}
            onClick={onPhaseClick}
          />
        ))}
      </div>
    </div>
  );
}
