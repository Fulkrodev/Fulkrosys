"use client";

/**
 * ReadinessScoreCard · score madurez ENS + bloqueantes (MB-13.5 · ADR-035).
 *
 * Reutiliza query admin-dashboard cache compartido NextActionCard +
 * PhaseProgressWizard (TanStack Query · SSE refresh MB-13.3).
 *
 * Muestra:
 *   - Score readiness (0-100) headline
 *   - Estimación días hasta certificación (si aplica)
 *   - Lista bloqueantes activos (top 5 del checklist M09)
 *
 * Coherencia visual: Card shadcn + Progress + theme tokens.
 */
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Target } from "lucide-react";

import { getProjectDashboard } from "@/lib/admin-dashboard/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  projectId: string;
}

export function ReadinessScoreCard({ projectId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-dashboard", projectId],
    queryFn: () => getProjectDashboard(projectId),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  if (isLoading) {
    return (
      <Card data-testid="readiness-score-card-skeleton">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const score = data.readiness_score;
  const days = data.estimated_days_to_certification;
  const blockers = data.blocking_issues;

  return (
    <Card data-testid="readiness-score-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Target className="h-5 w-5" aria-hidden="true" />
          Madurez ENS
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-4xl font-bold tabular-nums">{score}%</span>
            {days !== null && (
              <span className="text-sm text-muted-foreground">
                {days === 0
                  ? "Conformidad alcanzada"
                  : `~${days} días est.`}
              </span>
            )}
          </div>
          <Progress value={score} aria-label="Madurez ENS" />
          <p className="text-xs text-muted-foreground">
            Categoría {data.category} · Fase {data.phase_index + 1} de{" "}
            {data.phase_total}
          </p>
        </div>

        {blockers.length > 0 ? (
          <div>
            <p className="mb-2 flex items-center gap-2 text-sm font-medium text-destructive">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              {blockers.length} bloqueante{blockers.length === 1 ? "" : "s"}
            </p>
            <ul className="list-disc space-y-1 pl-6 text-sm text-muted-foreground">
              {blockers.slice(0, 3).map((issue, idx) => (
                <li key={idx}>{issue}</li>
              ))}
              {blockers.length > 3 && (
                <li className="list-none italic">
                  + {blockers.length - 3} más
                </li>
              )}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Sin bloqueantes activos
          </p>
        )}
      </CardContent>
    </Card>
  );
}
