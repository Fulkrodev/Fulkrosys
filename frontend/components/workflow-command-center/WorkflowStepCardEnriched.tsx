/**
 * WorkflowStepCardEnriched · per sub-paso AHORA expanded · sub-atom 1.C.D.B.2 v3.8.
 *
 * Renderiza enriched fields del template + state derived task:
 *   - description_detailed_es + rationale_es
 *   - actors badges
 *   - completion_criteria_detailed (checklist)
 *   - deliverable_codes (chips)
 *   - AdaptationBadge inline
 *   - CTAs: Marcar completo · Abrir drawer detalle
 */
"use client";

import * as React from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDot,
  ClipboardList,
  FileText,
  Loader2,
  Users2,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { useAdvanceStep } from "@/hooks/useWorkflowCommandCenter";
import type {
  EnrichedStepState,
  ProjectDimsLike,
} from "@/lib/api/workflow-command-center";

import { AdaptationBadge } from "./AdaptationBadge";

interface WorkflowStepCardEnrichedProps {
  step: EnrichedStepState;
  dims: ProjectDimsLike;
  projectId: string;
  variant?: "ahora" | "compact";
  onOpenDetail?: (step: EnrichedStepState) => void;
}

export function WorkflowStepCardEnriched({
  step,
  dims,
  projectId,
  variant = "compact",
  onOpenDetail,
}: WorkflowStepCardEnrichedProps) {
  const [expanded, setExpanded] = React.useState(variant === "ahora");
  const advanceMutation = useAdvanceStep();

  const handleAdvance = () => {
    advanceMutation.mutate(
      { projectId, templateId: step.template_id },
      {
        onSuccess: () => {
          toast.success(`Paso "${step.title}" marcado completo`);
        },
        onError: (err) => {
          toast.error(
            `Error: ${err instanceof Error ? err.message : String(err)}`,
          );
        },
      },
    );
  };

  const isCompleted = step.status === "completed";
  const isAhora = variant === "ahora";

  return (
    <Card
      className={
        isAhora
          ? "border-l-4 border-l-primary shadow-md"
          : isCompleted
            ? "border-l-4 border-l-emerald-500 opacity-75"
            : "border-l-2 border-l-foreground/20"
      }
    >
      <CardContent className={isAhora ? "pt-5 pb-4 space-y-3" : "py-3 px-4 space-y-2"}>
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              {isCompleted ? (
                <CheckCircle2 className="size-4 text-emerald-700" />
              ) : isAhora ? (
                <CircleDot className="size-4 text-primary animate-pulse" />
              ) : (
                <CircleDot className="size-3.5 text-foreground/40" />
              )}
              <h4
                className={
                  isAhora ? "text-base font-semibold" : "text-sm font-medium"
                }
              >
                {step.title}
              </h4>
              {step.is_enriched && (
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  enriched
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap text-xs text-foreground/70">
              <span>Fase {step.phase}</span>
              {step.order_within_phase !== null && (
                <>
                  <span>·</span>
                  <span>paso {step.order_within_phase}</span>
                </>
              )}
              {step.estimated_days !== null && (
                <>
                  <span>·</span>
                  <span>{step.estimated_days}d estimado</span>
                </>
              )}
              <span>·</span>
              <span
                className={
                  step.urgency_score >= 75
                    ? "text-red-600 font-semibold"
                    : step.urgency_score >= 50
                      ? "text-amber-600 font-medium"
                      : "text-foreground/70"
                }
              >
                urgencia {step.urgency_score}
              </span>
            </div>
          </div>
          {!isAhora && (
            <button
              type="button"
              onClick={() => setExpanded((x) => !x)}
              className="text-foreground/70 hover:text-foreground"
              aria-label={expanded ? "Colapsar" : "Expandir"}
            >
              {expanded ? (
                <ChevronDown className="size-4" />
              ) : (
                <ChevronRight className="size-4" />
              )}
            </button>
          )}
        </div>

        {/* Body expanded */}
        {(expanded || isAhora) && (
          <div className={isAhora ? "space-y-3" : "space-y-2 text-xs"}>
            <div className="flex items-center gap-2 flex-wrap">
              <AdaptationBadge step={step} dims={dims} />
              {step.actors.length > 0 && (
                <Badge variant="secondary" className="text-[10px]">
                  <Users2 className="size-2.5 mr-1" />
                  {step.actors.length} actores
                </Badge>
              )}
              {step.deliverable_codes.length > 0 && (
                <Badge variant="secondary" className="text-[10px]">
                  <FileText className="size-2.5 mr-1" />
                  {step.deliverable_codes.length} entregas
                </Badge>
              )}
            </div>

            {step.description_detailed_es && isAhora && (
              <p className="text-sm text-foreground/80 whitespace-pre-line">
                {step.description_detailed_es}
              </p>
            )}

            {step.rationale_es && isAhora && (
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs uppercase font-semibold text-foreground/70 mb-1">
                  Por qué ahora
                </p>
                <p className="text-sm text-foreground/80">{step.rationale_es}</p>
              </div>
            )}

            {step.completion_criteria_detailed.length > 0 && isAhora && (
              <div>
                <p className="text-xs uppercase font-semibold text-foreground/70 mb-1.5 flex items-center gap-1">
                  <ClipboardList className="size-3" />
                  Criterios completion
                </p>
                <ul className="space-y-1">
                  {step.completion_criteria_detailed.map((c, idx) => (
                    <li
                      key={idx}
                      className="flex gap-2 text-xs text-foreground/80"
                    >
                      <span className="text-foreground/30">○</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {step.deliverable_codes.length > 0 && isAhora && (
              <div className="flex flex-wrap gap-1">
                {step.deliverable_codes.map((code) => (
                  <Badge key={code} variant="outline" className="text-[10px]">
                    {code}
                  </Badge>
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-1">
              {!isCompleted && (
                <Button
                  size="sm"
                  onClick={handleAdvance}
                  disabled={advanceMutation.isPending}
                >
                  {advanceMutation.isPending ? (
                    <>
                      <Loader2 className="mr-1 size-3 animate-spin" />
                      Marcando…
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="mr-1 size-3" />
                      Marcar completo
                    </>
                  )}
                </Button>
              )}
              {onOpenDetail && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onOpenDetail(step)}
                >
                  <FileText className="mr-1 size-3" />
                  Ver detalle
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
