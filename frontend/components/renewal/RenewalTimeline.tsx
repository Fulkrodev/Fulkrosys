"use client";

/**
 * RenewalTimeline · 8 milestones pre-renovación (SAN-E v3.MB-3.4).
 *
 * Wired al backend M27 GET /renewal/timeline (commit MB-3.D 4a17834).
 * 8 milestones default seed: prep · review_docs · gap_close ·
 * pentest_refresh · evidencia_refresh · dossier · auditor_contact · audit_window.
 *
 * Responsive: horizontal desktop · vertical stack mobile.
 * Click milestone → modal con detalles + status + notas.
 */
import * as React from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import { useRenewalStatus } from "@/hooks/useRenewalStatus";
import type { MilestoneStatus, RenewalMilestone } from "@/lib/admin-renewal/api";

const MILESTONE_LABELS: Record<string, string> = {
  prep: "Preparación",
  review_docs: "Revisión docs",
  gap_close: "Cierre gaps",
  pentest_refresh: "Pentest refresh",
  evidencia_refresh: "Evidencias",
  dossier: "Dossier",
  auditor_contact: "Contacto auditor",
  audit_window: "Auditoría",
};

const STATUS_LABEL: Record<MilestoneStatus, string> = {
  pendiente: "Pendiente",
  en_progreso: "En curso",
  completado: "Completado",
  bloqueado: "Bloqueado",
  no_aplica: "No aplica",
};

function StatusBadge({ status }: { status: MilestoneStatus }) {
  const variant: "secondary" | "info" | "success" | "danger" | "outline" = (
    {
      pendiente: "secondary",
      en_progreso: "info",
      completado: "success",
      bloqueado: "danger",
      no_aplica: "outline",
    } as const
  )[status];
  return <Badge variant={variant}>{STATUS_LABEL[status]}</Badge>;
}

function statusVisual(status: MilestoneStatus) {
  if (status === "completado") {
    return {
      Icon: CheckCircle2,
      iconClass: "text-fulkro-success",
      ringClass: "border-fulkro-success bg-fulkro-success/10",
      labelClass: "text-fulkro-success font-semibold",
      connectorClass: "bg-fulkro-success",
    };
  }
  if (status === "en_progreso") {
    return {
      Icon: Clock,
      iconClass: "text-fulkro-warning",
      ringClass: "border-fulkro-warning bg-fulkro-warning/10 animate-pulse",
      labelClass: "text-fulkro-warning font-bold",
      connectorClass: "bg-fulkro-ink-200",
    };
  }
  if (status === "bloqueado") {
    return {
      Icon: XCircle,
      iconClass: "text-fulkro-danger",
      ringClass: "border-fulkro-danger bg-fulkro-danger/10",
      labelClass: "text-fulkro-danger font-bold",
      connectorClass: "bg-fulkro-ink-200",
    };
  }
  return {
    Icon: Circle,
    iconClass: "text-fulkro-ink-400",
    ringClass: "border-fulkro-ink-200 bg-white",
    labelClass: "text-fulkro-ink-500",
    connectorClass: "bg-fulkro-ink-200",
  };
}

interface RenewalTimelineProps {
  projectId: string;
}

export function RenewalTimeline({ projectId }: RenewalTimelineProps) {
  const { timeline } = useRenewalStatus(projectId);
  const [selected, setSelected] = React.useState<RenewalMilestone | null>(null);

  if (timeline.isLoading) {
    return <Skeleton className="h-32" />;
  }

  if (!timeline.data) return null;

  const milestones = timeline.data.milestones;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-[color:var(--fulkro-title)]">
          Hitos pre-renovación{" "}
          <TooltipENS term="workflow_retainer_cierre" iconSize={14} />
          <Badge variant="secondary" className="ml-auto">
            {timeline.data.progress.completed} / {timeline.data.progress.total}{" "}
            completados
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Desktop horizontal */}
        <div className="hidden md:block">
          <div className="relative flex items-start justify-between">
            <div className="absolute left-[18px] right-[18px] top-[18px] h-0.5 bg-fulkro-ink-200" />
            {milestones.map((m, idx) => {
              const v = statusVisual(m.status);
              const label = MILESTONE_LABELS[m.milestone_code] ?? m.milestone_code;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setSelected(m)}
                  className="relative z-10 flex min-w-[110px] flex-col items-center gap-2 px-1 transition-transform hover:scale-105"
                >
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-full border-2",
                      v.ringClass,
                    )}
                  >
                    <v.Icon
                      size={16}
                      strokeWidth={2.4}
                      className={v.iconClass}
                    />
                  </div>
                  <span className={cn("text-xs", v.labelClass)}>{label}</span>
                  {m.due_date ? (
                    <span className="text-[10px] text-fulkro-ink-400">
                      {new Date(m.due_date).toLocaleDateString("es-ES")}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>

        {/* Mobile vertical */}
        <div className="flex flex-col gap-3 md:hidden">
          {milestones.map((m, idx) => {
            const v = statusVisual(m.status);
            const isLast = idx === milestones.length - 1;
            const label = MILESTONE_LABELS[m.milestone_code] ?? m.milestone_code;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setSelected(m)}
                className="flex gap-3 text-left"
              >
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full border-2",
                      v.ringClass,
                    )}
                  >
                    <v.Icon size={14} strokeWidth={2.4} className={v.iconClass} />
                  </div>
                  {!isLast ? (
                    <div className={cn("mt-1 w-0.5 flex-1", v.connectorClass)} />
                  ) : null}
                </div>
                <div className="flex flex-1 flex-col gap-0.5 pb-3">
                  <span className={cn("text-sm", v.labelClass)}>{label}</span>
                  {m.due_date ? (
                    <span className="text-xs text-fulkro-ink-400">
                      Vence:{" "}
                      {new Date(m.due_date).toLocaleDateString("es-ES")}
                    </span>
                  ) : null}
                  <StatusBadge status={m.status} />
                </div>
              </button>
            );
          })}
        </div>
      </CardContent>

      {/* Modal detalles milestone */}
      <Dialog
        open={selected !== null}
        onOpenChange={(v) => {
          if (!v) setSelected(null);
        }}
      >
        <DialogContent>
          {selected ? (
            <>
              <DialogHeader>
                <DialogTitle className="flex flex-wrap items-center gap-2 text-[color:var(--fulkro-title)]">
                  {MILESTONE_LABELS[selected.milestone_code] ??
                    selected.milestone_code}
                  <StatusBadge status={selected.status} />
                </DialogTitle>
                <DialogDescription>
                  {selected.due_date
                    ? `Vence ${new Date(selected.due_date).toLocaleDateString(
                        "es-ES",
                      )} · `
                    : ""}
                  Código:{" "}
                  <code className="rounded bg-fulkro-ink-50 px-1 py-0.5 font-mono text-[11px]">
                    {selected.milestone_code}
                  </code>
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-col gap-3 text-sm">
                {selected.completed_at ? (
                  <p className="text-fulkro-success">
                    ✓ Completado el{" "}
                    {new Date(selected.completed_at).toLocaleDateString("es-ES")}
                  </p>
                ) : null}
                {selected.responsable ? (
                  <p className="text-fulkro-ink-500">
                    Responsable:{" "}
                    <span className="font-mono text-xs">{selected.responsable}</span>
                  </p>
                ) : null}
                {selected.notes ? (
                  <div className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-3">
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-fulkro-ink-400">
                      Notas
                    </p>
                    <p className="text-xs text-fulkro-ink-700">{selected.notes}</p>
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
