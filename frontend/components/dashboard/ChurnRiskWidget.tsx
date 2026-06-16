"use client";

/**
 * ChurnRiskWidget · /admin/dashboard widget (Sesión 3B-2B.3 Phase X.4d).
 *
 * Compact churn-risk surface for the admin dashboard · top 3 critical+high
 * retainers at risk · "Ver todos" link to /admin/finance.
 *
 * Migrated from former standalone route /admin/retainers/churn-risk (84 LOC)
 * which became a redirect when R23 strict cleanup eliminated cross-cliente
 * top-nav entries. Widget pattern preferred: visibility at dashboard glance
 * without dedicated page.
 *
 * Reuses ChurnRiskList component data shape · NO new backend endpoints
 * (listChurnRiskAdmin + triggerScanChurnAdmin existing).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ChevronRight, Loader2 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  listChurnRiskAdmin,
  triggerScanChurnAdmin,
} from "@/lib/billing/api";
import type { ChurnRiskRow, RetainerRiskLevel } from "@/lib/billing/schemas";

const COMPACT_LIMIT = 3;

function riskVariant(
  level: RetainerRiskLevel,
): "danger" | "warning" | "info" | "success" {
  switch (level) {
    case "critical":
      return "danger";
    case "high":
      return "warning";
    case "medium":
      return "info";
    default:
      return "success";
  }
}

export function ChurnRiskWidget() {
  const queryClient = useQueryClient();

  const query = useQuery<ChurnRiskRow[]>({
    queryKey: ["admin", "churn-risk", "widget"],
    queryFn: () => listChurnRiskAdmin(),
    staleTime: 30_000,
  });
  const rows = query.data ?? [];
  const loading = query.isLoading;
  const error = query.error
    ? query.error instanceof Error
      ? query.error.message
      : "No se pudo cargar churn risk"
    : null;

  const scanMut = useMutation({
    mutationFn: () => triggerScanChurnAdmin(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["admin", "churn-risk", "widget"],
      });
    },
  });
  const scanning = scanMut.isPending;

  const topCritical = rows
    .filter((r) => r.risk_level === "critical" || r.risk_level === "high")
    .slice(0, COMPACT_LIMIT);

  return (
    <Card data-testid="dashboard-churn-risk-widget">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-fulkro-warning-700" aria-hidden />
          <CardTitle className="text-base">Retainers en riesgo</CardTitle>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-label="Re-escanear churn risk"
          disabled={scanning}
          onClick={() => scanMut.mutate()}
        >
          {scanning ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            "Re-escanear"
          )}
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm">
        {loading ? (
          <p className="text-fulkro-ink-700">Cargando…</p>
        ) : error ? (
          <p
            role="alert"
            className="rounded-md bg-fulkro-danger-50 px-2 py-1 text-xs text-fulkro-danger-700"
          >
            {error}
          </p>
        ) : topCritical.length === 0 ? (
          <p className="text-fulkro-ink-700">
            Sin retainers críticos · todo en orden.
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {topCritical.map((r) => (
              <li
                key={r.retainer_id}
                className="flex items-center justify-between gap-2 rounded-md border border-fulkro-ink-100 px-2 py-1.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fulkro-ink-900">
                    {r.client_name ?? `Retainer ${r.retainer_id.slice(0, 8)}`}
                  </p>
                  <p className="truncate text-xs text-fulkro-ink-700">
                    {r.recommended_action ?? "Revisar señales"}
                  </p>
                </div>
                <Badge variant={riskVariant(r.risk_level)} className="shrink-0">
                  {r.risk_level}
                </Badge>
              </li>
            ))}
          </ul>
        )}

        <Link
          href="/admin/finance"
          className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-fulkro-primary-700 hover:underline"
        >
          Ver todos en Finanzas <ChevronRight className="h-3 w-3" />
        </Link>
      </CardContent>
    </Card>
  );
}
