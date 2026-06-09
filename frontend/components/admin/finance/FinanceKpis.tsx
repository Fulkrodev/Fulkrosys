"use client";

/**
 * FinanceKpis · 4 KPI cards admin finance dashboard (MB-18.5 ADR-040).
 *
 * Visual coherence MB-13/14/15/16/17: shadcn Card + Badge + lucide
 * icons (Banknote, Wallet, Hourglass, AlertTriangle) + fulkro palette.
 */
import { AlertTriangle, Banknote, Hourglass, Wallet } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { FinanceKpis as KpisData } from "@/lib/billing/schemas";

interface FinanceKpisProps {
  kpis: KpisData | null;
  loading: boolean;
}

export function FinanceKpis({ kpis, loading }: FinanceKpisProps) {
  if (loading || kpis === null) {
    return (
      <div
        className="grid gap-4 md:grid-cols-4"
        data-testid="finance-kpis-loading"
      >
        {[0, 1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="py-4">
              <div className="h-4 w-24 bg-fulkro-ink-100 rounded animate-pulse" />
              <div className="h-8 w-32 bg-fulkro-ink-100 rounded animate-pulse mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const overdueAlert = kpis.overdue_count > 0;

  return (
    <div className="grid gap-4 md:grid-cols-4" data-testid="finance-kpis">
      <Card data-testid="kpi-billed">
        <CardContent className="py-4">
          <p className="text-xs uppercase text-fulkro-ink-500 flex items-center gap-1">
            <Banknote className="h-3 w-3" />
            Facturado este mes
          </p>
          <p className="text-2xl font-semibold mt-2">
            {kpis.billed_this_month_eur} €
          </p>
        </CardContent>
      </Card>

      <Card data-testid="kpi-paid">
        <CardContent className="py-4">
          <p className="text-xs uppercase text-fulkro-ink-500 flex items-center gap-1">
            <Wallet className="h-3 w-3" />
            Cobrado este mes
          </p>
          <p className="text-2xl font-semibold mt-2 text-fulkro-success-700">
            {kpis.paid_this_month_eur} €
          </p>
        </CardContent>
      </Card>

      <Card data-testid="kpi-pending">
        <CardContent className="py-4">
          <p className="text-xs uppercase text-fulkro-ink-500 flex items-center gap-1">
            <Hourglass className="h-3 w-3" />
            Pendiente cobro
          </p>
          <p className="text-2xl font-semibold mt-2 text-fulkro-warning-700">
            {kpis.pending_total_eur} €
          </p>
        </CardContent>
      </Card>

      <Card
        data-testid="kpi-overdue"
        className={overdueAlert ? "border-fulkro-danger-500" : ""}
      >
        <CardContent className="py-4">
          <p className="text-xs uppercase text-fulkro-ink-500 flex items-center gap-1">
            <AlertTriangle
              className={`h-3 w-3 ${overdueAlert ? "text-fulkro-danger-700" : ""}`}
            />
            Vencidos &gt; 30d
          </p>
          <p
            className={`text-2xl font-semibold mt-2 ${overdueAlert ? "text-fulkro-danger-700" : ""}`}
          >
            {kpis.overdue_count}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
