"use client";

/**
 * MarcosPreparaSection · "Lo que Marcos está preparando" (1.D.G.E v3.11).
 *
 * Read-only informational · steps actor=admin status=in_progress.
 * R29 sostener: NO coercitive countdown · NO acciones · informational only.
 *
 * Format: "🟡 Marcos prepara: {step_title} · estará listo aprox {N} días"
 */
import * as React from "react";
import { ChevronDown, ChevronRight, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";

export interface MarcosPreparaSectionProps {
  steps: EnrichedStepState[];
  defaultExpanded?: boolean;
}

export function MarcosPreparaSection({
  steps,
  defaultExpanded = true,
}: MarcosPreparaSectionProps) {
  const [expanded, setExpanded] = React.useState(defaultExpanded);

  // Filter steps actor=admin status=in_progress
  const marcosWorking = steps.filter((s) => {
    const actor = s.primary_actor ?? "admin";
    const status = s.dependency_status ?? s.status;
    return actor === "admin" && status === "in_progress";
  });

  if (marcosWorking.length === 0) return null;

  return (
    <Card
      className="border-amber-200/60 dark:border-amber-900/40"
      data-testid="marcos-prepara-section"
    >
      <CardHeader
        className="cursor-pointer pb-3"
        onClick={() => setExpanded((x) => !x)}
        role="button"
        aria-expanded={expanded}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded((x) => !x);
          }
        }}
      >
        <CardTitle className="text-sm font-semibold flex items-center gap-2 text-amber-700 dark:text-amber-400">
          {expanded ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <Clock className="size-4" />
          Lo que Marcos está preparando
          <Badge variant="outline" className="ml-auto text-xs">
            {marcosWorking.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 space-y-2">
          {marcosWorking.map((step) => (
            <MarcosPreparaItem key={step.template_id} step={step} />
          ))}
          <p className="text-[11px] italic text-muted-foreground pt-1 leading-relaxed">
            Cuando esté listo te avisaremos. Sin prisa por tu lado.
          </p>
        </CardContent>
      )}
    </Card>
  );
}

function MarcosPreparaItem({ step }: { step: EnrichedStepState }) {
  const days =
    step.estimated_days_to_complete ?? step.estimated_days ?? null;
  return (
    <div
      className="rounded border bg-muted/20 p-3 text-sm"
      data-testid={`marcos-prepara-item-${step.template_id}`}
    >
      <div className="font-medium text-foreground/85">🟡 {step.title}</div>
      {days !== null && (
        <div className="text-xs text-muted-foreground mt-1">
          Estará listo aprox {days} día{days === 1 ? "" : "s"}
        </div>
      )}
    </div>
  );
}
