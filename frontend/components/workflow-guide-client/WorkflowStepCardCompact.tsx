"use client";

/**
 * WorkflowStepCardCompact · sub-atom 1.C.D.C.1 v3.8.
 *
 * Card compact para sección PRÓXIMOS PASOS · 1-line info friendly.
 *
 * R29 sostener · NO "urgente" · NO "atrasado" · NO countdown.
 * Solo título + fase + CTA "Ver más".
 */
import * as React from "react";
import { ArrowRight, CalendarDays } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";

interface WorkflowStepCardCompactProps {
  step: EnrichedStepState;
  onOpenDetail?: (step: EnrichedStepState) => void;
}

export function WorkflowStepCardCompact({
  step,
  onOpenDetail,
}: WorkflowStepCardCompactProps) {
  return (
    <Card
      className="border-l-2 border-l-blue-200 transition-colors hover:border-l-blue-400"
      onClick={() => onOpenDetail?.(step)}
      role={onOpenDetail ? "button" : undefined}
      tabIndex={onOpenDetail ? 0 : undefined}
      onKeyDown={(event) => {
        if (
          onOpenDetail &&
          (event.key === "Enter" || event.key === " ")
        ) {
          event.preventDefault();
          onOpenDetail(step);
        }
      }}
    >
      <CardContent className="flex items-center gap-3 px-4 py-3">
        <CalendarDays
          className="size-4 shrink-0 text-blue-400"
          strokeWidth={2.3}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-[color:var(--fulkro-title)]">
            {step.title}
          </p>
          <p className="text-xs text-[color:var(--fulkro-muted)]">
            Fase {step.phase}
          </p>
        </div>
        {onOpenDetail && (
          <ArrowRight
            className="size-4 shrink-0 text-blue-400"
            strokeWidth={2.3}
            aria-hidden
          />
        )}
      </CardContent>
    </Card>
  );
}
