"use client";

/**
 * AuditAccompanimentClienteView · cliente read-only timeline.
 * Sesión 3B-4 Ejecutable 7.5 Phase 7.5.3 (2026-05-27).
 *
 * R29 cliente friendly · sin technical jargon · single-project per cliente LIMIT 1.
 * SSE auto-update via useClientProjectEvents existing hook (Pattern #14 + #21 reuse).
 * Cliente-mínimo filosofía: cliente RECIBE timeline updates · NO opera proceso.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { CheckCircle2, Circle, Sparkles } from "lucide-react";
import { useEffect } from "react";

import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  auditAccompanimentClienteApi,
} from "@/lib/api/audit-accompaniment-cliente";
import type { AccompanimentTimeline } from "@/lib/api/audit-accompaniment";

interface Props {
  projectId?: string | null;
}

const BASICO_FRIENDLY_LABELS: Record<string, string> = {
  not_started: "Aún no hemos empezado tu acompañamiento",
  declaration_drafted: "Tu consultor está redactando tu declaración",
  declaration_signed: "Has firmado tu declaración",
  declaration_published: "Tu declaración está publicada en sede",
  ccn_communicated: "Hemos comunicado tu declaración al CCN",
  periodic_review_scheduled: "Hemos programado tu revisión anual",
  completed: "Has completado tu ciclo de cumplimiento ENS",
};

const MEDIO_ALTO_FRIENDLY_LABELS: Record<string, string> = {
  not_started: "Aún no hemos empezado tu acompañamiento",
  preparation: "Estamos preparando tu plan de implantación",
  docs_collected: "Hemos completado tu documentación ENS",
  internal_audit_scheduled: "Tu auditoría interna está programada",
  internal_audit_completed: "Tu auditoría interna ha pasado correctamente",
  enac_audit_scheduled: "Tu auditoría ENAC está agendada",
  enac_audit_in_progress: "Tu auditoría ENAC está en curso",
  enac_findings_resolution: "Resolviendo los hallazgos de tu auditoría",
  enac_audit_passed: "Has aprobado tu auditoría ENAC",
  certificate_issued: "Tienes tu certificado ENS vigente 2 años",
  biannual_renewal_scheduled: "Hemos programado tu renovación bianual",
};

function getFriendlyLabel(branch: string, state: string): string {
  const map = branch === "MEDIO_ALTO" ? MEDIO_ALTO_FRIENDLY_LABELS : BASICO_FRIENDLY_LABELS;
  return map[state] ?? state;
}

export function AuditAccompanimentClienteView({ projectId }: Props) {
  const queryClient = useQueryClient();

  const { data: timeline, isLoading, error } = useQuery<AccompanimentTimeline>({
    queryKey: ["client-audit-accompaniment-timeline"],
    queryFn: () => auditAccompanimentClienteApi.getTimeline(),
    staleTime: 30_000,
  });

  useClientProjectEvents(projectId ?? null, {
    invalidateQueries: [["client-audit-accompaniment-timeline"]],
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Cargando tu certificación...
        </CardContent>
      </Card>
    );
  }

  if (error || !timeline) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Aún no hemos iniciado tu acompañamiento de certificación. Tu consultor te
          avisará cuando estemos listos.
        </CardContent>
      </Card>
    );
  }

  const branchFriendlyName =
    timeline.category_branch === "MEDIO_ALTO"
      ? "ENS Medio/Alto (auditoría ENAC)"
      : "ENS Básico (autodeclaración)";

  const orderedStates =
    timeline.category_branch === "MEDIO_ALTO"
      ? [
          "not_started",
          "preparation",
          "docs_collected",
          "internal_audit_scheduled",
          "internal_audit_completed",
          "enac_audit_scheduled",
          "enac_audit_in_progress",
          "enac_findings_resolution",
          "enac_audit_passed",
          "certificate_issued",
          "biannual_renewal_scheduled",
        ]
      : [
          "not_started",
          "declaration_drafted",
          "declaration_signed",
          "declaration_published",
          "periodic_review_scheduled",
          "completed",
        ];

  const currentIdx = orderedStates.findIndex((s) => s === timeline.current_state);
  const transitionsByState = timeline.transitions.reduce<Record<string, typeof timeline.transitions[0]>>(
    (acc, t) => {
      acc[t.to_state] = t;
      return acc;
    },
    {},
  );

  return (
    <Card data-testid="cliente-audit-accompaniment-view">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-fulkro-info" strokeWidth={2.3} />
          Tu certificación ENS
        </CardTitle>
        <CardDescription>
          {branchFriendlyName} ·{" "}
          <strong>{getFriendlyLabel(timeline.category_branch, timeline.current_state)}</strong>
          {timeline.is_terminal && (
            <Badge variant="success" className="ml-2">
              Completado
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="space-y-3" data-testid="cliente-states-timeline">
          {orderedStates.map((state, idx) => {
            const isCompleted = idx < currentIdx;
            const isCurrent = idx === currentIdx;
            const transition = transitionsByState[state];

            return (
              <li
                key={state}
                className={`flex items-start gap-3 rounded-md border p-3 ${
                  isCurrent ? "border-fulkro-info bg-fulkro-info/5" : ""
                }`}
                data-testid={`cliente-state-${state}`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-5 w-5 text-fulkro-success" strokeWidth={2.3} />
                ) : isCurrent ? (
                  <Circle className="h-5 w-5 text-fulkro-info animate-pulse" strokeWidth={2.3} />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground" strokeWidth={2.3} />
                )}
                <div className="flex-1">
                  <p className="font-medium">
                    {getFriendlyLabel(timeline.category_branch, state)}
                  </p>
                  {transition && (
                    <p className="text-xs text-muted-foreground">
                      {format(new Date(transition.advanced_at), "PPp", { locale: es })}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
