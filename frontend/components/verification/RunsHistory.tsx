"use client";

import {
  CheckCircle2,
  CircleDashed,
  FileText,
  Loader2,
  Play,
  ShieldX,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useGenerateReport,
  useVerificationRuns,
} from "@/hooks/useVerification";
import { RUN_STATUS_LABELS } from "@/lib/labels";
import type { RunSummary } from "@/lib/verification-types";
import { cn, formatDate } from "@/lib/utils";

const STATUS_ICON: Record<
  string,
  { icon: typeof CheckCircle2; color: string; bg: string }
> = {
  completed: { icon: CheckCircle2, color: "text-fulkro-success", bg: "bg-fulkro-success/10" },
  pending: { icon: CircleDashed, color: "text-fulkro-ink-500", bg: "bg-fulkro-ink-100" },
  authorized: { icon: Play, color: "text-fulkro-info", bg: "bg-fulkro-info/10" },
  phase1_running: { icon: Play, color: "text-fulkro-primary-500", bg: "bg-fulkro-primary-500/10" },
  phase2_running: { icon: Play, color: "text-fulkro-primary-500", bg: "bg-fulkro-primary-500/10" },
  phase3_validating: {
    icon: Play,
    color: "text-fulkro-primary-500",
    bg: "bg-fulkro-primary-500/10",
  },
  cancelled: { icon: ShieldX, color: "text-fulkro-danger", bg: "bg-fulkro-danger/10" },
  failed: { icon: ShieldX, color: "text-fulkro-danger", bg: "bg-fulkro-danger/10" },
};

export function RunsHistory({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useVerificationRuns(projectId);
  const generate = useGenerateReport(projectId);

  async function downloadReport(run: RunSummary, codigo: "E-702" | "E-703") {
    try {
      const r = await generate.mutateAsync({
        runId: run.id,
        body: { template_codigo: codigo, generate_pdf: true, sign: true },
      });
      toast.success(`${codigo} generado`, {
        description: `DOCX: ${r.docx_path.split("/").pop()}`,
      });
    } catch (err) {
      toast.error(`No se pudo generar ${codigo}`, {
        description: (err as Error).message,
      });
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Historial de ejecuciones</CardTitle>
        </CardHeader>
        <CardContent className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={14} className="animate-spin" /> cargando ejecuciones…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Historial de ejecuciones</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          Error: {(error as Error).message}
        </CardContent>
      </Card>
    );
  }

  const runs = data?.runs ?? [];
  if (runs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Historial de ejecuciones</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-base font-medium text-[color:var(--fulkro-muted)]">
          Todavía no se ha ejecutado ninguna verificación.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Historial de ejecuciones</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="flex flex-col gap-3">
          {runs.map((r) => {
            const style = STATUS_ICON[r.status] ?? STATUS_ICON.pending;
            const Icon = style.icon;
            const canReport = r.status === "completed";
            return (
              <li
                key={r.id}
                className="flex flex-col gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] p-3 md:flex-row md:items-center md:justify-between"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "rounded-full p-2",
                      style.bg,
                      style.color,
                    )}
                    aria-hidden
                  >
                    <Icon size={14} />
                  </div>
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-fulkro-primary-700">
                      <span>{r.category}</span>
                      <span className="rounded bg-fulkro-ink-100 px-1.5 text-[10px] font-mono text-fulkro-ink-500">
                        {r.id.slice(0, 8)}
                      </span>
                      <span
                        className={cn(
                          "rounded px-1.5 text-[10px] font-semibold uppercase",
                          style.bg,
                          style.color,
                        )}
                      >
                        {RUN_STATUS_LABELS[r.status] ?? r.status}
                      </span>
                    </p>
                    <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                      {r.completed_at
                        ? `Completado ${formatDate(r.completed_at)}`
                        : r.created_at
                          ? `Creado ${formatDate(r.created_at)}`
                          : "—"}
                      {r.total_findings > 0 && (
                        <>
                          {" · "}
                          <span className="font-medium text-fulkro-primary-700">
                            {r.total_findings}
                          </span>{" "}
                          hallazgos ({r.critical_count} críticos,{" "}
                          {r.high_count} altos)
                        </>
                      )}
                      {r.security_score !== null && (
                        <>
                          {" · score "}
                          <span className="font-medium text-fulkro-primary-700">
                            {r.security_score}/100
                          </span>
                        </>
                      )}
                    </p>
                  </div>
                </div>
                {canReport && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadReport(r, "E-702")}
                      disabled={generate.isPending}
                      className="gap-1"
                    >
                      <FileText size={12} /> E-702
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadReport(r, "E-703")}
                      disabled={generate.isPending}
                      className="gap-1"
                    >
                      <FileText size={12} /> E-703
                    </Button>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
