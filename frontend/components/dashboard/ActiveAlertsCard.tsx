"use client";

/**
 * ActiveAlertsCard · alertas activas per proyecto inline (MB-13.5 · ADR-035).
 *
 * Reusa endpoint MB-13.4 GET /projects/{id}/alerts. SSE alert_new event
 * (MB-13.3 useProjectEvents) invalida ["alerts", projectId] auto.
 *
 * Muestra top 3 alertas (severity-aware borders) + link "Ver todas".
 * Si no hay alertas, mensaje placeholder.
 */
import { useQuery } from "@tanstack/react-query";
import { Bell, ChevronRight } from "lucide-react";
import Link from "next/link";

import { listProjectAlerts } from "@/lib/admin-alerts/api";
import type {
  AlertResponse,
  AlertSeverity,
} from "@/lib/admin-alerts/schemas";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function severityBorder(severity: AlertSeverity): string {
  if (severity === "critical")
    return "border-l-fulkro-danger bg-fulkro-danger/10";
  if (severity === "warning")
    return "border-l-fulkro-warning bg-fulkro-warning/10";
  return "border-l-fulkro-info bg-fulkro-info/10";
}

interface Props {
  projectId: string;
}

export function ActiveAlertsCard({ projectId }: Props) {
  const { data: alerts = [], isLoading } = useQuery<AlertResponse[]>({
    queryKey: ["alerts", projectId],
    queryFn: () => listProjectAlerts(projectId),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <Card data-testid="active-alerts-card-skeleton">
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="active-alerts-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Bell className="h-5 w-5" aria-hidden="true" />
          Alertas activas{alerts.length > 0 && ` (${alerts.length})`}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Sin alertas activas para este proyecto
          </p>
        ) : (
          <ul className="space-y-2" role="list">
            {alerts.slice(0, 3).map((alert) => (
              <li
                key={alert.id}
                className={cn(
                  "rounded-md border-l-4 p-3",
                  severityBorder(alert.severity),
                )}
              >
                <p className="text-sm font-medium">{alert.title}</p>
                {alert.description && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {alert.description}
                  </p>
                )}
                {alert.action_url && (
                  <Link
                    href={alert.action_url}
                    className="mt-2 inline-flex items-center gap-1 text-xs text-fulkro-info hover:underline"
                  >
                    Ir
                    <ChevronRight
                      className="h-3 w-3"
                      aria-hidden="true"
                    />
                  </Link>
                )}
              </li>
            ))}
            {alerts.length > 3 && (
              <li>
                <Link
                  href="/admin/alerts"
                  className="text-xs text-fulkro-info hover:underline"
                >
                  Ver {alerts.length - 3} más →
                </Link>
              </li>
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
