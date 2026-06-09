"use client";

/**
 * FinancialPanel real · M15 wired (SAN-E v3.MB-3.2).
 *
 * Sustituye stub `EmptyStateUpcoming` post-FASE-9 con UI completa cableada
 * al backend M15 (commit MB-3.F · financial-summary + aapp-chain + send +
 * existing CRUD invoices).
 *
 * 4 secciones:
 * A. KPIs cards · 4 metricas (facturado · pagado · pendiente · vencidas)
 * B. Proximo hito · countdown + amount + Generate CTA + AAPPBillingStatusCard
 * C. MilestoneTimeline · 8 phases workflow ENS visualizadas
 * D. InvoicesList · DataTable historico facturas con acciones
 */
import * as React from "react";
import { Loader2, TrendingDown, TrendingUp, Wallet, Zap } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import { useFinancialSummary } from "@/hooks/useFinancialSummary";

import { AAPPBillingStatusCard } from "./AAPPBillingStatusCard";
import { InvoicesList } from "./InvoicesList";
import { MilestoneTimeline } from "./MilestoneTimeline";

function fmtEuro(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n);
}

interface KPIProps {
  label: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  accent?: "default" | "success" | "warning" | "danger";
}

function KPI({ label, value, subtitle, icon, accent = "default" }: KPIProps) {
  const accentColor = {
    default: "text-fulkro-ink-700",
    success: "text-fulkro-success",
    warning: "text-fulkro-warning",
    danger: "text-fulkro-danger",
  }[accent];
  return (
    <Card>
      <CardContent className="flex items-start gap-3 pt-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-fulkro-ink-50 text-fulkro-ink-500">
          {icon}
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs uppercase tracking-wide text-fulkro-ink-400">
            {label}
          </span>
          <span
            className={`text-2xl font-bold tabular-nums ${accentColor} text-[color:var(--fulkro-title)]`}
          >
            {value}
          </span>
          {subtitle ? (
            <span className="text-xs text-fulkro-ink-500">{subtitle}</span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function FinancialPanel({ projectId }: { projectId: string }) {
  const fin = useFinancialSummary(projectId);
  const summary = fin.summary.data;
  const isLoading = fin.summary.isLoading;

  const onGenerate = async () => {
    if (!summary?.next_milestone?.milestone_index) return;
    try {
      const inv = await fin.generate.mutateAsync(
        summary.next_milestone.milestone_index,
      );
      toast.success(
        `Factura ${inv.numero_correlativo ?? inv.id.slice(0, 8)} generada`,
      );
    } catch {
      toast.error("Error al generar factura");
    }
  };

  if (isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-40" />
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        <Card>
          <CardContent className="py-8 text-center text-sm text-fulkro-ink-500">
            No se pudo cargar el resumen financiero.
          </CardContent>
        </Card>
      </div>
    );
  }

  const totals = summary.totals;
  const overdueCount = summary.invoices_overdue_count;
  const ratioFacturado =
    totals.invoiced > 0
      ? Math.round((totals.paid / totals.invoiced) * 100)
      : 0;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      {/* A · KPIs */}
      <section className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <KPI
          label="Facturado"
          value={fmtEuro(totals.invoiced)}
          subtitle={`${summary.invoices_count} facturas emitidas`}
          icon={<TrendingUp size={18} strokeWidth={2.4} />}
        />
        <KPI
          label="Cobrado"
          value={fmtEuro(totals.paid)}
          subtitle={`${ratioFacturado}% del facturado`}
          icon={<Wallet size={18} strokeWidth={2.4} />}
          accent="success"
        />
        <KPI
          label="Pendiente cobro"
          value={fmtEuro(totals.outstanding)}
          subtitle={`${summary.invoices_pending_count} pendientes`}
          icon={<TrendingDown size={18} strokeWidth={2.4} />}
          accent={totals.outstanding > 0 ? "warning" : "default"}
        />
        <KPI
          label="Vencidas"
          value={String(overdueCount)}
          subtitle="Facturas con vencimiento superado"
          icon={<Zap size={18} strokeWidth={2.4} />}
          accent={overdueCount > 0 ? "danger" : "default"}
        />
      </section>

      {/* B · Próximo hito + AAPP card */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-[color:var(--fulkro-title)]">
              Próximo hito facturable{" "}
              <TooltipENS term="workflow_retainer_cierre" iconSize={14} />
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.next_milestone?.label ? (
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <span className="text-xs uppercase tracking-wide text-fulkro-ink-400">
                    Hito #{summary.next_milestone.milestone_index ?? "—"}
                  </span>
                  <span className="text-lg font-bold text-[color:var(--fulkro-title)]">
                    {summary.next_milestone.label}
                  </span>
                  <span className="text-2xl font-bold tabular-nums text-fulkro-info">
                    {fmtEuro(summary.next_milestone.amount_eur)}
                  </span>
                  {summary.next_milestone.billing_trigger ? (
                    <Badge variant="secondary" className="w-fit">
                      Trigger: {summary.next_milestone.billing_trigger}
                    </Badge>
                  ) : null}
                </div>
                <Button
                  variant="primary"
                  onClick={() => void onGenerate()}
                  disabled={fin.generate.isPending}
                >
                  {fin.generate.isPending ? (
                    <Loader2
                      size={14}
                      className="animate-spin"
                      strokeWidth={2.4}
                    />
                  ) : null}
                  Generar factura
                </Button>
              </div>
            ) : (
              <p className="text-sm text-fulkro-ink-500">
                No hay hitos pendientes. Todos los milestones del contrato
                están facturados o el contrato no tiene hitos definidos.
              </p>
            )}
          </CardContent>
        </Card>

        <AAPPBillingStatusCard projectId={projectId} />
      </div>

      {/* C · Timeline · #45 E0 · base = fase REAL del proyecto (no milestone_index) */}
      <MilestoneTimeline
        currentPhaseIndex={summary.current_phase_index ?? null}
      />

      {/* D · InvoicesList */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-[color:var(--fulkro-title)]">
            Histórico facturas
          </h2>
          <Badge variant="secondary">
            {summary.invoices_count}{" "}
            {summary.invoices_count === 1 ? "factura" : "facturas"}
          </Badge>
        </div>
        <InvoicesList projectId={projectId} />
      </section>
    </div>
  );
}
