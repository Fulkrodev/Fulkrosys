"use client";

import { AlertCircle, Clock, Loader2, ListChecks } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRemediationPlan } from "@/hooks/useVerification";
import { ZFP_CLASSIFICATION_LABELS } from "@/lib/labels";
import type { Severity } from "@/lib/verification-types";
import { cn } from "@/lib/utils";

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "border-fulkro-danger bg-fulkro-danger/5",
  high: "border-fulkro-danger/50 bg-fulkro-danger/5",
  medium: "border-fulkro-warning bg-fulkro-warning/5",
  low: "border-fulkro-info bg-fulkro-info/5",
  info: "border-[color:var(--fulkro-surface-glass-border)] bg-fulkro-ink-100/50",
};

const SEVERITY_PILL: Record<Severity, string> = {
  critical: "bg-fulkro-danger text-white",
  high: "bg-fulkro-danger-500 text-white",
  medium: "bg-fulkro-warning text-white",
  low: "bg-fulkro-info text-white",
  info: "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
};

export function RemediationPlan({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useRemediationPlan(projectId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plan de remediación</CardTitle>
        </CardHeader>
        <CardContent className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={14} className="animate-spin" /> calculando prioridad…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plan de remediación</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          Error: {(error as Error).message}
        </CardContent>
      </Card>
    );
  }

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plan de remediación</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-base font-medium text-[color:var(--fulkro-muted)]">
          No hay hallazgos abiertos que requieran remediación.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2.5">
            <ListChecks size={22} strokeWidth={2.2} /> Plan de remediación ({items.length})
          </CardTitle>
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Ordenado por severidad × effort (quick wins primero)
          </p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {items.map((it, i) => {
          const deadlineDate = new Date(it.sla.deadline);
          const hoursLeft = it.sla.hours_remaining;
          return (
            <article
              key={it.finding_id}
              className={cn(
                "rounded-md border p-3 text-sm",
                SEVERITY_STYLES[it.severity],
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 rounded-full bg-fulkro-primary-700 px-2 py-0.5 text-[10px] font-semibold text-white">
                    #{i + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-fulkro-primary-700">{it.title}</p>
                    <p className="mt-0.5 font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                      {it.affected_host}
                      {it.ens_primary_measure
                        ? ` · ${it.ens_primary_measure}`
                        : ""}
                    </p>
                  </div>
                </div>
                <span
                  className={cn(
                    "rounded px-2 py-0.5 text-[11px] font-semibold uppercase",
                    SEVERITY_PILL[it.severity],
                  )}
                >
                  {it.severity}
                </span>
              </div>
              {it.remediation_summary && (
                <p className="mt-2 text-sm font-medium text-[color:var(--fulkro-body)]">
                  {it.remediation_summary}
                </p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px]">
                <span
                  className={cn(
                    "inline-flex items-center gap-1",
                    it.sla.overdue ? "text-fulkro-danger" : "text-fulkro-ink-500",
                  )}
                >
                  {it.sla.overdue ? (
                    <AlertCircle size={12} />
                  ) : (
                    <Clock size={12} />
                  )}
                  Vencimiento {deadlineDate.toLocaleDateString("es-ES")}
                  {it.sla.overdue
                    ? ` — VENCIDA hace ${Math.abs(Math.round(hoursLeft))}h`
                    : ` — ${Math.round(hoursLeft)}h restantes`}
                </span>
                {it.remediation_effort && (
                  <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-semibold text-fulkro-ink-500">
                    {it.remediation_effort}
                  </span>
                )}
                <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-mono text-fulkro-ink-500">
                  {ZFP_CLASSIFICATION_LABELS[it.classification] ?? it.classification}
                </span>
              </div>
            </article>
          );
        })}
      </CardContent>
    </Card>
  );
}
