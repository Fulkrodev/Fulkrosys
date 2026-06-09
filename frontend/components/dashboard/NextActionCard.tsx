"use client";

/**
 * NextActionCard · home admin proyecto top-of-page (MB-13.1 · ADR-035).
 *
 * Aglutina la respuesta del endpoint dashboard agregado y muestra:
 *   - Badge "Fase X de 10: <label>"
 *   - Acción primaria (top-priority NextAction) con CTA a deeplink motor
 *   - Acciones secundarias colapsables
 *   - Score readiness (esquina superior derecha)
 *   - Bloqueantes activos (extraídos checklist M09)
 *   - Estimación días hasta certificación
 *
 * Polling baseline 30s · SSE refines event-driven en MB-13.3.
 *
 * Coherencia visual ADR-035: solo theme tokens (Card/Button/Badge shadcn +
 * fulkro-success/danger) · solo iconos lucide-react · solo Tailwind scale.
 */
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Lock,
} from "lucide-react";
import Link from "next/link";

import { getProjectDashboard } from "@/lib/admin-dashboard/api";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface Props {
  projectId: string;
}

export function NextActionCard({ projectId }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-dashboard", projectId],
    queryFn: () => getProjectDashboard(projectId),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  if (isLoading) {
    return (
      <Card data-testid="next-action-card-skeleton">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-8 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return null;
  }

  const primary = data.next_actions[0];

  if (!primary) {
    return (
      <Card data-testid="next-action-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2
              className="h-5 w-5 text-fulkro-success"
              aria-hidden="true"
            />
            Sin acciones pendientes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Proyecto en {data.current_phase_label} · Fase{" "}
            {data.phase_index + 1} de {data.phase_total}
          </p>
          {data.estimated_days_to_certification !== null && (
            <p className="mt-2 text-sm">
              Estimación certificación:{" "}
              <strong>
                {data.estimated_days_to_certification === 0
                  ? "Conformidad alcanzada"
                  : `~${data.estimated_days_to_certification} días`}
              </strong>
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="next-action-card">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <Badge variant="outline" className="mb-2">
              Fase {data.phase_index + 1} de {data.phase_total}:{" "}
              {data.current_phase_label}
            </Badge>
            <CardTitle>Siguiente acción</CardTitle>
            {data.estimated_days_to_certification !== null &&
              data.estimated_days_to_certification > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Estimación certificación: ~
                  {data.estimated_days_to_certification} días
                </p>
              )}
          </div>
          <div
            className="text-right"
            aria-label={`Madurez ENS: ${data.readiness_score}%`}
          >
            <div className="text-3xl font-bold tabular-nums">
              {data.readiness_score}%
            </div>
            <div className="text-xs text-muted-foreground">Madurez ENS</div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-lg font-medium">{primary.label}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              <Clock className="mr-1 h-3 w-3" aria-hidden="true" />~
              {primary.estimated_minutes} min
            </Badge>
            <Badge variant="outline">{primary.motor}</Badge>
            {primary.urgent && (
              <Badge variant="danger">
                <AlertTriangle className="mr-1 h-3 w-3" aria-hidden="true" />
                Urgente
              </Badge>
            )}
            {primary.blocking && (
              <Badge variant="danger">
                <Lock className="mr-1 h-3 w-3" aria-hidden="true" />
                Bloqueante fase
              </Badge>
            )}
          </div>
          <Link
            href={primary.action_url}
            className={cn(
              buttonVariants({ variant: "primary" }),
              "w-full sm:w-auto",
            )}
          >
            {primary.cta}
            <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        {data.next_actions.length > 1 && (
          <details className="rounded-md border p-3">
            <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
              Otras {data.next_actions.length - 1} acciones pendientes
            </summary>
            <ul className="mt-3 space-y-2">
              {data.next_actions.slice(1).map((action) => (
                <li
                  key={action.action_id}
                  className="flex items-start justify-between gap-2 border-b pb-2 last:border-b-0"
                >
                  <div className="min-w-0 flex-1">
                    <Link
                      href={action.action_url}
                      className="text-sm font-medium hover:underline"
                    >
                      {action.label}
                    </Link>
                    <span className="ml-2 text-xs text-muted-foreground">
                      ({action.motor} · ~{action.estimated_minutes} min)
                    </span>
                  </div>
                  {action.urgent && (
                    <Badge variant="danger" className="text-xs">
                      Urgente
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}

        {data.blocking_issues.length > 0 && (
          <div className="rounded-md bg-destructive/10 p-3" role="alert">
            <p className="mb-2 flex items-center gap-2 text-sm font-medium text-destructive">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              Bloqueantes activos
            </p>
            <ul className="list-disc space-y-1 pl-6 text-sm text-destructive">
              {data.blocking_issues.map((issue, idx) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
