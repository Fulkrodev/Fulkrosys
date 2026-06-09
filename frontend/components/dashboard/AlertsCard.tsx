"use client";

import { Bell, CheckCircle2, RefreshCw } from "lucide-react";

import { RAGDot } from "@/components/data/RAGBadge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAlerts } from "@/hooks/useDashboardData";

export function AlertsCard() {
  const { data, isLoading, isError, refetch, isRefetching } = useAlerts();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Bell size={22} strokeWidth={2.2} /> Alertas
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ul className="space-y-2" aria-busy>
            {Array.from({ length: 2 }).map((_, i) => (
              <li
                key={i}
                className="h-10 animate-pulse rounded-md bg-fulkro-ink-100/70"
              />
            ))}
          </ul>
        ) : isError ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-fulkro-danger">
              No pude obtener las alertas.
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void refetch()}
              disabled={isRefetching}
              className="self-start"
              data-testid="alerts-card-retry"
            >
              <RefreshCw
                size={14}
                className={isRefetching ? "animate-spin" : ""}
              />
              Reintentar
            </Button>
          </div>
        ) : data && data.length > 0 ? (
          <ul className="space-y-1.5">
            {data.map((alert) => (
              <li
                key={alert.id}
                className="flex items-start gap-3 rounded-md border border-fulkro-ink-300/40 px-3 py-2"
              >
                <RAGDot status={alert.severity} className="mt-1.5 h-2 w-2" />
                <div className="min-w-0 flex-1 text-sm">
                  <p className="text-fulkro-ink-700">{alert.message}</p>
                  <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                    {alert.project ? `${alert.project} · ` : ""}
                    {new Date(alert.createdAt).toLocaleDateString("es-ES", {
                      day: "2-digit",
                      month: "short",
                    })}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex items-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
            <CheckCircle2
              size={16}
              className="text-emerald-700"
              aria-hidden
            />
            Todo tranquilo · sin alertas pendientes.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
