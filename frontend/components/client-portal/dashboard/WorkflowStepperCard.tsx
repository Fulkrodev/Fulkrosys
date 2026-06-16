"use client";

/**
 * WorkflowStepperCard · zone 3 dashboard.
 *
 * 10-phase visual stepper · current phase highlighted · link to /workflow.
 */
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PHASE_LABELS, PHASE_ORDER } from "@/lib/adaptive-dashboard";

interface Props {
  currentPhase: string | null;
  phaseStep: number | null;
}

export function WorkflowStepperCard({ currentPhase, phaseStep }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Tu workflow</CardTitle>
        <Link
          href="/client-portal/workflow"
          className="text-sm font-bold text-[color:var(--fulkro-accent)] hover:underline"
        >
          Ver detalle →
        </Link>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2" data-testid="workflow-stepper">
          {PHASE_ORDER.map((phase, index) => {
            const stepNum = index + 1;
            const isCurrent = phase === currentPhase;
            const isPast = phaseStep != null && stepNum < phaseStep;
            return (
              <li
                key={phase}
                className={`flex items-center gap-3 rounded-lg px-3 py-1.5 ${
                  isCurrent
                    ? "bg-[color:var(--fulkro-accent)]/15 ring-1 ring-[color:var(--fulkro-accent)]/40"
                    : ""
                }`}
              >
                <span
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ${
                    isCurrent
                      ? "bg-[color:var(--fulkro-accent)] text-white"
                      : isPast
                      ? "bg-fulkro-success-500/20 text-fulkro-success-700"
                      : "bg-fulkro-surface-glass text-[color:var(--fulkro-muted)]"
                  }`}
                >
                  {isPast ? "✓" : stepNum}
                </span>
                <span
                  className={`text-sm font-medium ${
                    isCurrent
                      ? "font-bold text-[color:var(--fulkro-title)]"
                      : isPast
                      ? "text-fulkro-success-700"
                      : "text-[color:var(--fulkro-muted)]"
                  }`}
                >
                  {PHASE_LABELS[phase]}
                </span>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
