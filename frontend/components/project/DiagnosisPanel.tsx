"use client";

import {
  AlertCircle,
  Building2,
  Database,
  GitBranch,
  Loader2,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  Users2,
  type LucideIcon,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { RAGDot } from "@/components/data/RAGBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useDiagnosis,
  useDiagnosisLegalObligationsList,
  useDiagnosisProcessesList,
  useDiagnosisStakeholdersList,
  useGenerateDiagnosisDocx,
  useGenerateDiagnosisReport,
  useRunDiagnosis,
} from "@/hooks/useDiagnosis";
import { downloadDiagnosisDocx } from "@/lib/api/diagnosis";
import type {
  DiagnosisRunOut,
  LegalObligationOut,
  ProcessOut,
  StakeholderOut,
} from "@/lib/api/diagnosis";
import type { RagStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

type AttitudeBucket = "sponsor" | "neutral" | "blocker";

function attitudeBucket(actitud: string | null | undefined): AttitudeBucket {
  if (!actitud) return "neutral";
  const lower = actitud.toLowerCase();
  if (
    lower.includes("sponsor") ||
    lower.includes("patrocin") ||
    lower.includes("aliado")
  ) {
    return "sponsor";
  }
  if (
    lower.includes("blocker") ||
    lower.includes("bloque") ||
    lower.includes("opos")
  ) {
    return "blocker";
  }
  return "neutral";
}

function criticidadToRag(criticidad: string | null | undefined): RagStatus {
  if (!criticidad) return "amber";
  const lower = criticidad.toLowerCase();
  if (lower === "alta" || lower === "high" || lower === "red") return "red";
  if (lower === "baja" || lower === "low" || lower === "green") return "green";
  return "amber";
}

interface MaturitySummary {
  level: string;
  score_pct: number | null;
}

function readMaturity(run: DiagnosisRunOut | undefined): MaturitySummary | null {
  if (!run) return null;
  const scoring = run.maturity_scoring as
    | Record<string, unknown>
    | null
    | undefined;
  if (!scoring) return null;
  const level = String(
    (scoring.level as string | undefined) ??
      (scoring.nivel as string | undefined) ??
      "L?",
  );
  const rawScore =
    (scoring.score_pct as number | undefined) ??
    (scoring.score as number | undefined) ??
    null;
  const score_pct =
    typeof rawScore === "number" ? rawScore : rawScore == null ? null : Number(rawScore);
  return { level, score_pct: Number.isFinite(score_pct) ? score_pct : null };
}

export function DiagnosisPanel({ projectId }: { projectId: string }) {
  const latest = useDiagnosis(projectId);
  const stakeholders = useDiagnosisStakeholdersList(projectId);
  const processes = useDiagnosisProcessesList(projectId);
  const legalObligations = useDiagnosisLegalObligationsList(projectId);

  const runDiagnosisMut = useRunDiagnosis(projectId);
  const generateReportMut = useGenerateDiagnosisReport(projectId);
  const generateDocxMut = useGenerateDiagnosisDocx(projectId);
  const [docxBusy, setDocxBusy] = React.useState(false);

  const isLoading =
    latest.isLoading ||
    stakeholders.isLoading ||
    processes.isLoading ||
    legalObligations.isLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-24 w-full rounded-lg" />
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Skeleton className="h-96 w-full rounded-lg" />
          <Skeleton className="h-96 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  const latestRun = latest.data;
  const hasRun = Boolean(latestRun) && !latest.isError;
  const maturity = readMaturity(latestRun);
  const runId =
    (latestRun?.run_id as string | undefined) ??
    ((latestRun as { id?: string } | undefined)?.id as string | undefined);

  async function runFullDiagnosis() {
    try {
      await runDiagnosisMut.mutateAsync({
        sector: "generico",
        triggered_by: "marcos",
      });
      toast.success("Diagnostico M21 ejecutado");
    } catch (err) {
      toast.error(
        `No se pudo ejecutar el diagnostico: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    }
  }

  async function generateReport() {
    if (!runId) {
      toast.error("No hay run de diagnostico activo");
      return;
    }
    try {
      await generateReportMut.mutateAsync(runId);
      toast.success("Informe regenerado");
    } catch (err) {
      toast.error(
        `Error generando informe: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    }
  }

  async function generateDocx() {
    if (!runId) {
      toast.error("No hay run de diagnostico activo");
      return;
    }
    setDocxBusy(true);
    try {
      // Clic único en cadena: regenerar informe -> renderizar DOCX -> descargar.
      // Regenerar es barato y garantiza que el DOCX refleja el diagnostico
      // actual, y evita un 422 por un "Regenerar informe" previo invisible.
      // Un fallo en cualquier eslabon cae al catch con un toast claro.
      await generateReportMut.mutateAsync(runId);
      await generateDocxMut.mutateAsync(runId);
      const blob = await downloadDiagnosisDocx(projectId, runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `diagnostico_fase1_${runId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("DOCX descargado");
    } catch (err) {
      toast.error(
        `Error generando el DOCX: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    } finally {
      setDocxBusy(false);
    }
  }

  if (!hasRun) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={<Sparkles className="h-8 w-8" strokeWidth={2.2} />}
            title="Diagnostico organizativo no ejecutado"
            description="Lanza un run de Motor 21 para evaluar madurez ENS, identificar stakeholders y obligaciones cruzadas."
            action={{
              label: runDiagnosisMut.isPending
                ? "Ejecutando..."
                : "Ejecutar diagnostico (M21)",
              onClick: runFullDiagnosis,
              variant: "primary",
            }}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Madurez actual{" "}
              <TooltipENS text="Nivel de madurez ENS de tu organización (L0 inexistente · L1 inicial · L2 repetible · L3 definido · L4 gestionado · L5 optimizado). La mayoría de PYMEs aterriza en L3 tras adecuación." />
            </p>
            <p className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
              {maturity?.level ?? "L?"}
              {maturity?.score_pct != null && (
                <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                  {" "}
                  - {maturity.score_pct}%
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={runDiagnosisMut.isPending}
              onClick={runFullDiagnosis}
            >
              {runDiagnosisMut.isPending ? (
                <Loader2 size={14} strokeWidth={2.2} className="animate-spin" />
              ) : (
                <PlayCircle size={14} strokeWidth={2.2} />
              )}
              Re-ejecutar diagnostico
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={generateReportMut.isPending || !runId}
              onClick={generateReport}
            >
              {generateReportMut.isPending ? (
                <Loader2 size={14} strokeWidth={2.2} className="animate-spin" />
              ) : (
                <Sparkles size={14} strokeWidth={2.2} />
              )}
              Regenerar informe
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={docxBusy || !runId}
              onClick={generateDocx}
            >
              {docxBusy ? (
                <Loader2 size={14} strokeWidth={2.2} className="animate-spin" />
              ) : (
                <Sparkles size={14} strokeWidth={2.2} />
              )}
              Generar DOCX
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <DiagnosisOrgPanel
          stakeholders={stakeholders.data?.stakeholders ?? []}
          processes={processes.data?.processes ?? []}
          legalObligations={legalObligations.data?.legal_obligations ?? []}
          stakeholdersError={stakeholders.isError}
          processesError={processes.isError}
          legalError={legalObligations.isError}
        />
        <DiagnosisTechPanel />
      </div>
    </div>
  );
}

function DiagnosisOrgPanel({
  stakeholders,
  processes,
  legalObligations,
  stakeholdersError,
  processesError,
  legalError,
}: {
  stakeholders: StakeholderOut[];
  processes: ProcessOut[];
  legalObligations: LegalObligationOut[];
  stakeholdersError: boolean;
  processesError: boolean;
  legalError: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Building2 size={22} strokeWidth={2.2} /> Diagnostico organizativo - M21
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Section icon={Users2} title="Personas clave">
          {stakeholdersError ? (
            <Alert variant="danger">
              <AlertCircle className="h-4 w-4" strokeWidth={2.2} />
              <AlertTitle>Error cargando stakeholders</AlertTitle>
              <AlertDescription>
                No fue posible recuperar la lista. Intenta refrescar.
              </AlertDescription>
            </Alert>
          ) : stakeholders.length === 0 ? (
            <EmptyState
              icon={<Users2 className="h-8 w-8" strokeWidth={2.2} />}
              title="Sin personas clave registradas"
              description="Anade stakeholders desde el diagnostico para mapear influencia y actitud."
            />
          ) : (
            <ul className="space-y-1.5">
              {stakeholders.slice(0, 5).map((s) => {
                const bucket = attitudeBucket(s.actitud);
                return (
                  <li
                    key={s.id}
                    className="flex items-center justify-between gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-1.5 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-bold text-[color:var(--fulkro-title)]">
                        {s.nombre}
                      </p>
                      <p className="truncate text-sm font-medium text-[color:var(--fulkro-muted)]">
                        {s.cargo ?? s.departamento ?? "-"}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "shrink-0 rounded-full px-2 py-0.5 text-xs font-bold",
                        bucket === "sponsor"
                          ? "bg-fulkro-success/10 text-fulkro-success"
                          : bucket === "blocker"
                            ? "bg-fulkro-danger/10 text-fulkro-danger"
                            : "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
                      )}
                    >
                      {bucket === "sponsor"
                        ? "Patrocinador"
                        : bucket === "blocker"
                          ? "Bloqueante"
                          : "Neutral"}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>

        <Section icon={GitBranch} title="Procesos de negocio">
          {processesError ? (
            <Alert variant="danger">
              <AlertCircle className="h-4 w-4" strokeWidth={2.2} />
              <AlertTitle>Error cargando procesos</AlertTitle>
              <AlertDescription>
                No fue posible recuperar la lista de procesos.
              </AlertDescription>
            </Alert>
          ) : processes.length === 0 ? (
            <EmptyState
              icon={<GitBranch className="h-8 w-8" strokeWidth={2.2} />}
              title="Sin procesos de negocio"
              description="Mapea procesos criticos para enlazar con MAGERIT y trazabilidad ENS."
            />
          ) : (
            <ul className="space-y-1.5">
              {processes.map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-1.5 text-sm"
                >
                  <div>
                    <p className="font-bold text-[color:var(--fulkro-title)]">
                      {p.nombre}
                    </p>
                    <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                      {p.propietario ?? "Sin owner"}
                      {p.rto_horas != null ? ` - RTO ${p.rto_horas}h` : ""}
                    </p>
                  </div>
                  <RAGDot status={criticidadToRag(p.criticidad)} className="h-2 w-2" />
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section icon={ShieldCheck} title="Obligaciones normativas cruzadas">
          {legalError ? (
            <Alert variant="danger">
              <AlertCircle className="h-4 w-4" strokeWidth={2.2} />
              <AlertTitle>Error cargando obligaciones</AlertTitle>
              <AlertDescription>
                No fue posible recuperar las obligaciones legales.
              </AlertDescription>
            </Alert>
          ) : legalObligations.length === 0 ? (
            <EmptyState
              icon={<ShieldCheck className="h-8 w-8" strokeWidth={2.2} />}
              title="Sin obligaciones normativas"
              description="Detecta articulos aplicables (RD 311, RGPD, NIS2, DORA) en el run de diagnostico."
            />
          ) : (
            <ul className="space-y-1.5 text-sm">
              {legalObligations.map((lo) => (
                <li
                  key={lo.id}
                  className="flex items-start justify-between gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="font-bold text-[color:var(--fulkro-title)]">
                      {lo.normativa}{" "}
                      {lo.articulo && (
                        <span className="font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                          {lo.articulo}
                        </span>
                      )}
                    </p>
                    <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                      {lo.alcance ?? lo.impacto_ens ?? "-"}
                    </p>
                  </div>
                  {lo.estado && (
                    <span className="shrink-0 rounded-full bg-fulkro-ink-100 px-2 py-0.5 text-xs font-medium text-[color:var(--fulkro-muted)]">
                      {lo.estado}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </CardContent>
    </Card>
  );
}

function DiagnosisTechPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Database size={22} strokeWidth={2.2} /> Diagnostico tecnico - M22
        </CardTitle>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={<Database className="h-8 w-8" strokeWidth={2.2} />}
          title="Motor 22 (diagnostico tecnico) en backlog"
          description="Activos, identidades, flujos de datos y vulnerabilidades aterrizan cuando M22 entre en operacion."
        />
      </CardContent>
    </Card>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="mb-2 flex items-center gap-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        <Icon size={12} strokeWidth={2.2} /> {title}
      </h3>
      {children}
    </section>
  );
}
