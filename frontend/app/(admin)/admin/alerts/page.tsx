"use client";

/**
 * /admin/alerts · panel completo alertas activas globales admin
 * (cierra dead link MB-13 · MB-14.fix · ADR-038).
 *
 * Reusa API client existing (lib/admin-alerts/api.ts MB-13.4 · ADR-035):
 *   GET  /api/v1/alerts/active            · global admin
 *   POST /api/v1/alerts/{id}/acknowledge  · marcar leida
 *
 * Filtros UI client-side: severity (info/warning/critical) · category.
 * Coherencia visual ADR-035: shadcn Card + Badge + Button · lucide
 * icons (Bell · AlertTriangle · CheckCircle2 · Filter) · fulkro
 * palette (info/warning/danger).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronRight,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  acknowledgeAlert,
  listActiveAlertsGlobal,
} from "@/lib/admin-alerts/api";
import type {
  AlertCategory,
  AlertResponse,
  AlertSeverity,
} from "@/lib/admin-alerts/schemas";
import { cn } from "@/lib/utils";

type SeverityFilter = "all" | AlertSeverity;
type CategoryFilter = "all" | AlertCategory;

const SEVERITY_FILTERS: { key: SeverityFilter; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "info", label: "Info" },
  { key: "warning", label: "Warning" },
  { key: "critical", label: "Critical" },
];

function severityBadgeVariant(
  severity: AlertSeverity,
): "info" | "warning" | "danger" {
  if (severity === "critical") return "danger";
  if (severity === "warning") return "warning";
  return "info";
}

function severityBorder(severity: AlertSeverity): string {
  if (severity === "critical") return "border-l-fulkro-danger";
  if (severity === "warning") return "border-l-fulkro-warning";
  return "border-l-fulkro-info";
}

export default function AdminAlertsPage() {
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");

  const { data: alerts = [], isLoading } = useQuery<AlertResponse[]>({
    queryKey: ["admin-alerts-global"],
    queryFn: listActiveAlertsGlobal,
    refetchInterval: 60_000,
  });

  const ackMutation = useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-alerts-global"] }),
  });

  const categories = useMemo(() => {
    const set = new Set<AlertCategory>();
    alerts.forEach((a) => set.add(a.category));
    return Array.from(set).sort();
  }, [alerts]);

  const filtered = useMemo(() => {
    return alerts.filter((a) => {
      if (severityFilter !== "all" && a.severity !== severityFilter)
        return false;
      if (categoryFilter !== "all" && a.category !== categoryFilter)
        return false;
      return true;
    });
  }, [alerts, severityFilter, categoryFilter]);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">Alertas activas</h1>
        <Badge variant={alerts.length > 0 ? "warning" : "secondary"}>
          {alerts.length}
        </Badge>
      </div>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4 text-fulkro-info" strokeWidth={2.3} />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Severidad:</span>
            {SEVERITY_FILTERS.map((f) => (
              <Button
                key={f.key}
                size="sm"
                variant={severityFilter === f.key ? "primary" : "outline"}
                onClick={() => setSeverityFilter(f.key)}
              >
                {f.label}
              </Button>
            ))}
          </div>

          {categories.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">Categoría:</span>
              <Button
                size="sm"
                variant={categoryFilter === "all" ? "primary" : "outline"}
                onClick={() => setCategoryFilter("all")}
              >
                Todas
              </Button>
              {categories.map((cat) => (
                <Button
                  key={cat}
                  size="sm"
                  variant={categoryFilter === cat ? "primary" : "outline"}
                  onClick={() => setCategoryFilter(cat)}
                >
                  {cat}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {isLoading ? (
        <Card>
          <CardContent className="space-y-2 p-6">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex items-center gap-3 p-6">
            <CheckCircle2
              className="h-6 w-6 text-fulkro-success"
              strokeWidth={2.3}
            />
            <div>
              <p className="font-medium">Sin alertas activas</p>
              <p className="text-sm text-muted-foreground">
                {alerts.length === 0
                  ? "Todo en orden · sistema sin alertas pendientes."
                  : "Sin alertas para los filtros seleccionados."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3">
          {filtered.map((alert) => (
            <li key={alert.id}>
              <AlertRow
                alert={alert}
                ackPending={ackMutation.isPending}
                onAck={() => ackMutation.mutate(alert.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AlertRow({
  alert,
  ackPending,
  onAck,
}: {
  alert: AlertResponse;
  ackPending: boolean;
  onAck: () => void;
}) {
  return (
    <Card className={cn("border-l-4", severityBorder(alert.severity))}>
      <CardContent className="flex flex-wrap items-start gap-3 p-4">
        <AlertTriangle
          className={cn(
            "mt-0.5 h-5 w-5 shrink-0",
            alert.severity === "critical"
              ? "text-fulkro-danger"
              : alert.severity === "warning"
                ? "text-fulkro-warning"
                : "text-fulkro-info",
          )}
          strokeWidth={2.3}
        />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">{alert.title}</h3>
            <Badge variant={severityBadgeVariant(alert.severity)}>
              {alert.severity}
            </Badge>
            <Badge variant="outline" className="font-mono text-xs">
              {alert.category}
            </Badge>
          </div>
          {alert.description && (
            <p className="mt-1 text-sm text-muted-foreground">
              {alert.description}
            </p>
          )}
          <p className="mt-1 text-xs text-muted-foreground">
            {new Date(alert.triggered_at).toLocaleString("es")}
            {alert.triggered_by ? ` · ${alert.triggered_by}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {alert.action_url && (
            <Link
              href={alert.action_url}
              className="text-sm text-fulkro-info hover:underline"
            >
              <span className="inline-flex items-center gap-1">
                Resolver
                <ChevronRight className="h-3 w-3" strokeWidth={2.3} />
              </span>
            </Link>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={onAck}
            disabled={ackPending}
          >
            {ackPending ? (
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle2 className="mr-1 h-3 w-3" strokeWidth={2.3} />
            )}
            Ack
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
