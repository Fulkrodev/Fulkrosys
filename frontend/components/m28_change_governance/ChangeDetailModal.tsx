"use client";

/**
 * ChangeDetailModal · Sub-atom 1.D.D.B v3.11.
 *
 * Detalle de un cambio: estado actual + materiality + impact vector +
 * tracking timeline. Si el cambio ya está assessed, muestra el detalle
 * completo via GET /impact. Si está en intake, muestra estado pending.
 *
 * Backend reuse:
 *  GET /api/v1/changes/projects/{pid}/changes/{cid}/impact
 */
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, Clock } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  IMPACT_QUESTION_LABELS,
  IMPACT_QUESTIONS,
  MATERIALITY_LEVEL_LABELS,
  MATERIALITY_LEVEL_VARIANTS,
  changesApi,
} from "@/lib/api/changes";

interface ChangeDetailModalProps {
  projectId: string;
  changeId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ChangeDetailModal({
  projectId,
  changeId,
  open,
  onOpenChange,
}: ChangeDetailModalProps) {
  const impactQuery = useQuery({
    queryKey: ["m28", "impact", projectId, changeId],
    queryFn: () => changesApi.getImpact(projectId, changeId),
    enabled: open && Boolean(changeId),
    retry: false,
  });

  const data = impactQuery.data;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        data-testid="change-detail-modal"
      >
        <DialogHeader>
          <DialogTitle>Detalle del cambio</DialogTitle>
          <DialogDescription>
            Estado · materiality · impact vector · tracking.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div
            className="rounded-md border p-2 text-xs"
            data-testid="change-id-info"
          >
            <span className="font-semibold">ID: </span>
            <code className="font-mono">#{changeId.slice(0, 12)}</code>
          </div>

          {impactQuery.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : impactQuery.isError ? (
            <Alert variant="info" data-testid="change-pending-assessment">
              <AlertTitle>Cambio aún sin evaluación</AlertTitle>
              <AlertDescription>
                El cambio está en estado <code>intake</code>. Completa el
                wizard para evaluarlo y ver el detalle del impacto.
              </AlertDescription>
            </Alert>
          ) : data ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase text-muted-foreground">
                    Materiality
                  </span>
                  <Badge
                    variant={
                      MATERIALITY_LEVEL_VARIANTS[data.materiality_level]
                    }
                    data-testid="change-materiality-badge"
                  >
                    {MATERIALITY_LEVEL_LABELS[data.materiality_level]}
                  </Badge>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase text-muted-foreground">
                    Score (0-100)
                  </span>
                  <span
                    className="text-2xl font-bold"
                    data-testid="change-score"
                  >
                    {data.materiality_score}
                  </span>
                </div>
              </div>

              <div
                className="rounded-md border p-3"
                data-testid="change-impact-vector"
              >
                <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                  Impact vector
                </p>
                <ul className="space-y-1 text-sm">
                  {IMPACT_QUESTIONS.map((q) => {
                    // Backend renames some keys in impact_vector
                    // (affects_documentation → document · etc). Buscar
                    // por sufijo conocido.
                    const compactKey = q.replace("affects_", "").replace(
                      "requires_",
                      "",
                    );
                    const valueByCompact =
                      data.impact_vector[compactKey] ??
                      data.impact_vector[q];
                    const isYes = Boolean(valueByCompact);
                    return (
                      <li
                        key={q}
                        className="flex items-center gap-2"
                        data-testid={`impact-${q}`}
                      >
                        {isYes ? (
                          <CheckCircle2
                            size={14}
                            className="text-fulkro-warning"
                          />
                        ) : (
                          <Circle
                            size={14}
                            className="text-fulkro-ink-300"
                          />
                        )}
                        <span
                          className={
                            isYes
                              ? "font-medium"
                              : "text-muted-foreground"
                          }
                        >
                          {IMPACT_QUESTION_LABELS[q]}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>

              <div
                className="rounded-md border bg-fulkro-info/5 p-3 text-sm"
                data-testid="change-timeline"
              >
                <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <Clock size={14} /> Tracking
                </p>
                <ol className="space-y-1.5 text-xs">
                  <TrackingStep
                    label="Solicitud intake"
                    done
                  />
                  <TrackingStep
                    label="Materiality engine evaluado"
                    done
                  />
                  <TrackingStep
                    label="Workflows requeridos auto-disparados"
                    done={false}
                    note="Pendiente activación por el equipo"
                  />
                  <TrackingStep
                    label="Notificación E-042 generada"
                    done={false}
                    note="Tras aprobación · auto-document"
                  />
                  <TrackingStep label="Cierre" done={false} />
                </ol>
              </div>
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function TrackingStep({
  label,
  done,
  note,
}: {
  label: string;
  done: boolean;
  note?: string;
}) {
  return (
    <li className="flex items-start gap-2">
      {done ? (
        <CheckCircle2 size={14} className="mt-[2px] text-fulkro-success" />
      ) : (
        <Circle size={14} className="mt-[2px] text-fulkro-ink-300" />
      )}
      <div className="flex flex-col">
        <span className={done ? "font-medium" : "text-muted-foreground"}>
          {label}
        </span>
        {note && (
          <span className="text-[11px] text-fulkro-ink-500">{note}</span>
        )}
      </div>
    </li>
  );
}
