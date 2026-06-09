"use client";

/**
 * WorkflowStepCardClient · sub-atom 1.C.D.C.1 v3.8.
 *
 * Card sub-paso AHORA expanded · adapted tono cliente (NO técnico admin).
 *
 * Diferencias clave vs WorkflowStepCardEnriched (admin):
 *   - "¿Qué tienes que hacer?" (NO "description_detailed_es")
 *   - "¿Por qué es importante?" (NO "rationale_es")
 *   - NO actors badges visibles (cliente NO entiende CISO+DPO+Comité)
 *   - NO AdaptationBadge (cliente no entiende dims técnicas)
 *   - NO urgency score visible (R29 · NO presión)
 *   - "Marcar como hecho" CTA friendly (NO "Validar" admin lingo)
 *   - Subir evidencias CTA si expected_evidence
 *
 * R29 sostener empírico · audit pre-commit grep "deadline" "urgente" 0 instances.
 */
import * as React from "react";
import { ArrowRight, CheckCircle2, CircleDot, FileUp, Info } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";

interface WorkflowStepCardClientProps {
  step: EnrichedStepState;
  onOpenDetail?: (step: EnrichedStepState) => void;
  onMarkDone?: (step: EnrichedStepState) => void;
}

function deliverableHint(step: EnrichedStepState): string | null {
  if (step.deliverable_codes.length === 0) return null;
  if (step.deliverable_codes.length === 1) {
    return `Necesitas preparar el documento ${step.deliverable_codes[0]}.`;
  }
  return `Necesitas preparar ${step.deliverable_codes.length} documentos cuando termines este paso.`;
}

export function WorkflowStepCardClient({
  step,
  onOpenDetail,
  onMarkDone,
}: WorkflowStepCardClientProps) {
  const hint = deliverableHint(step);

  return (
    <Card className="border-l-4 border-l-blue-500 shadow-md">
      <CardContent className="space-y-4 px-5 py-5">
        <div className="flex items-start gap-3">
          <CircleDot
            className="mt-1 size-5 shrink-0 text-blue-600"
            strokeWidth={2.3}
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold text-[color:var(--fulkro-title)]">
              {step.title}
            </h3>
            <p className="mt-1 text-xs font-medium uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Tu siguiente paso
            </p>
          </div>
        </div>

        {step.description_detailed_es && (
          <div>
            <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              ¿Qué tienes que hacer?
            </p>
            <p className="whitespace-pre-line text-sm text-[color:var(--fulkro-body)]">
              {step.description_detailed_es}
            </p>
          </div>
        )}

        {step.rationale_es && (
          <div className="rounded-lg bg-blue-50/60 p-3">
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-700">
              <Info className="size-3" strokeWidth={2.5} />
              ¿Por qué es importante?
            </p>
            <p className="text-sm text-[color:var(--fulkro-body)]">
              {step.rationale_es}
            </p>
          </div>
        )}

        {hint && (
          <p className="text-xs font-medium text-[color:var(--fulkro-muted)]">
            <FileUp className="mr-1 inline size-3" strokeWidth={2.3} />
            {hint}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {onMarkDone && step.status !== "completed" && (
            <Button size="sm" onClick={() => onMarkDone(step)}>
              <CheckCircle2 className="mr-1 size-3.5" strokeWidth={2.3} />
              Marcar como hecho
            </Button>
          )}
          {onOpenDetail && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onOpenDetail(step)}
            >
              Ver más detalle
              <ArrowRight className="ml-1 size-3.5" strokeWidth={2.3} />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
