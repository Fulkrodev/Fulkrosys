"use client";

/**
 * AlertBell · campana alertas activas top nav admin (MB-13.4 · ADR-035).
 *
 * Polling baseline 60s · refrescado por SSE alert_new event (MB-13.3 hook
 * ``useProjectEvents`` invalida ["alerts","active"] cuando llega event).
 * Click abre Popover con top 8 alertas + acknowledge inline + link
 * "Ver todas" → /admin/alerts (página completa MB-13.5).
 *
 * Coherencia visual: theme tokens (fulkro-danger / fulkro-warning /
 * fulkro-info) + Popover + Badge shadcn + iconos lucide-react.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, X } from "lucide-react";
import Link from "next/link";

import {
  acknowledgeAlert,
  listActiveAlertsGlobal,
} from "@/lib/admin-alerts/api";
import type { AlertResponse, AlertSeverity } from "@/lib/admin-alerts/schemas";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

function severityBorder(severity: AlertSeverity): string {
  if (severity === "critical") return "border-l-fulkro-danger bg-fulkro-danger/10";
  if (severity === "warning") return "border-l-fulkro-warning bg-fulkro-warning/10";
  return "border-l-fulkro-info bg-fulkro-info/10";
}

export function AlertBell() {
  const queryClient = useQueryClient();

  const { data: alerts = [] } = useQuery<AlertResponse[]>({
    queryKey: ["alerts", "active"],
    queryFn: listActiveAlertsGlobal,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const totalCount = alerts.length;
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="relative rounded-full p-2.5 text-white hover:bg-white/10"
          aria-label={`Alertas activas (${totalCount})`}
          data-testid="alert-bell"
        >
          <Bell size={20} strokeWidth={2.2} aria-hidden="true" />
          {totalCount > 0 && (
            <span
              className={cn(
                "absolute right-0.5 top-0.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-semibold text-white",
                criticalCount > 0
                  ? "bg-fulkro-danger"
                  : "bg-fulkro-primary-500",
              )}
              aria-hidden="true"
            >
              {totalCount}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-3">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold">Alertas activas</h3>
          {totalCount > 0 && (
            <Link
              href="/admin/alerts"
              className="text-xs text-fulkro-info hover:underline"
            >
              Ver todas
            </Link>
          )}
        </div>

        {alerts.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            Sin alertas activas
          </p>
        ) : (
          <ul className="max-h-80 space-y-2 overflow-y-auto" role="list">
            {alerts.slice(0, 8).map((alert) => (
              <li
                key={alert.id}
                className={cn(
                  "rounded-md border-l-4 p-3",
                  severityBorder(alert.severity),
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{alert.title}</p>
                    {alert.description && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {alert.description}
                      </p>
                    )}
                    {alert.action_url && (
                      <Link
                        href={alert.action_url}
                        className="mt-2 inline-block text-xs text-fulkro-info hover:underline"
                      >
                        Ir →
                      </Link>
                    )}
                  </div>
                  <button
                    type="button"
                    className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                    onClick={() => acknowledgeMutation.mutate(alert.id)}
                    disabled={acknowledgeMutation.isPending}
                    aria-label="Marcar como leída"
                    title="Marcar como leída"
                  >
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}
