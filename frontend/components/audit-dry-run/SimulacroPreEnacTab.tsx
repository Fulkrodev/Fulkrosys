"use client";

/**
 * SimulacroPreEnacTab · Sesión 3B-2B.10 Phase 10.4 (2026-05-27).
 *
 * Pattern P-CL2-4 ENRICH existing landing: tab embedded inside
 * AuditDryRunDashboard · NO new route. R23 project-scoped admin.
 *
 * Composes outputs orchestrator delgado (5 existing + 2 nuevos OPS-026 DRY):
 * - Score readiness overall
 * - Gap counts (total/critical/high) + coverage_pct
 * - audit_log integrity status (R6 hash chain inviolable preserved)
 * - Corrective loops opened per gap (state open/in_progress/closed)
 * - Signed PDF metadata (sha256 + Ed25519 signature)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  PlayCircle,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  simulacroPreEnacApi,
  type SimulacroReport,
} from "@/lib/api/simulacro-pre-enac";

interface Props {
  projectId: string;
}

export function SimulacroPreEnacTab({ projectId }: Props) {
  const queryClient = useQueryClient();

  const { data: lastReport, isLoading: lastReportLoading } = useQuery<SimulacroReport | null>({
    queryKey: ["simulacro-pre-enac-last-report", projectId],
    queryFn: () => simulacroPreEnacApi.getLastReport(projectId),
    staleTime: 30_000,
  });

  const executeMutation = useMutation({
    mutationFn: () => simulacroPreEnacApi.execute(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["simulacro-pre-enac-last-report", projectId],
      });
    },
  });

  const isExecuting = executeMutation.isPending;
  const currentReport = executeMutation.data ?? lastReport;

  return (
    <div className="space-y-6" data-testid="simulacro-pre-enac-tab">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-fulkro-info" strokeWidth={2.3} />
            Simulacro Pre-ENAC ·{" "}
            <TooltipENS text="Ejecuta una pasada interna completa simulando la auditoría ENAC: dry-run + DdA evidence gaps + workflow state + audit_log integrity (R6) + corrective loops automáticos + informe PDF firmado." />
          </CardTitle>
          <CardDescription>
            Orquestador delgado que compone 5 servicios existentes (dry-run M10+A11,
            gap matrix Phase C3, workflow admin Phase 1D, integrity hash chain SHA-256,
            informe PDF Phase C4) + 2 nuevos (audit_log integrity check, corrective
            loop state machine). Tiempo esperado 60-150s.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={() => executeMutation.mutate()}
            disabled={isExecuting}
            size="lg"
            data-testid="simulacro-pre-enac-execute-btn"
          >
            {isExecuting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={2.3} />
                Ejecutando simulacro Pre-ENAC...
              </>
            ) : (
              <>
                <PlayCircle className="mr-2 h-4 w-4" strokeWidth={2.3} />
                Ejecutar simulacro Pre-ENAC
              </>
            )}
          </Button>

          {lastReportLoading && !currentReport && (
            <p className="text-sm text-muted-foreground">Cargando último simulacro...</p>
          )}

          {!lastReportLoading && !currentReport && (
            <p className="text-sm text-muted-foreground">
              Sin simulacros previos. Ejecuta para detectar gaps antes de auditoría ENAC oficial.
            </p>
          )}
        </CardContent>
      </Card>

      {currentReport && <SimulacroReportDisplay report={currentReport} />}
    </div>
  );
}

function SimulacroReportDisplay({ report }: { report: SimulacroReport }) {
  const score = report.overall_readiness_score;
  const scoreColor = score >= 80 ? "success" : score >= 60 ? "warning" : "danger";

  return (
    <div className="space-y-4" data-testid="simulacro-report-display">
      <Card className="border-l-4 border-l-fulkro-info">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" strokeWidth={2.3} />
              Informe simulacro · {format(new Date(report.executed_at), "PPp", { locale: es })}
            </CardTitle>
            <Badge variant={scoreColor === "success" ? "success" : "warning"}>
              {score}% madurez
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Gaps totales" value={report.total_gaps} tone="default" />
            <Metric label="Críticos" value={report.critical_gaps} tone="danger" />
            <Metric label="High" value={report.high_gaps} tone="warning" />
            <Metric label="Cobertura DdA" value={`${report.coverage_pct.toFixed(1)}%`} tone="default" />
          </div>

          <IntegrityRow integrityOk={report.integrity_ok} firstBadSeq={report.integrity_first_bad_seq} />

          <div className="rounded-md border p-3 text-sm">
            <p className="font-medium mb-2">Bucles correctivos abiertos: {report.corrective_loops_opened}</p>
            {report.loops_metadata.length > 0 ? (
              <ul className="grid gap-1 md:grid-cols-2">
                {report.loops_metadata.slice(0, 10).map((loop) => (
                  <li
                    key={loop.loop_id}
                    className="flex items-center justify-between rounded border px-2 py-1 text-xs"
                  >
                    <span className="font-mono">{loop.gap_id ?? "?"}</span>
                    <Badge variant={loop.severity === "critical" ? "danger" : "warning"}>
                      {loop.severity ?? "?"}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">Sin gaps críticos/high detectados.</p>
            )}
          </div>

          <PdfMetadataRow report={report} />
        </CardContent>
      </Card>
    </div>
  );
}

function IntegrityRow({
  integrityOk,
  firstBadSeq,
}: {
  integrityOk: boolean;
  firstBadSeq: number | null;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border p-3 text-sm">
      {integrityOk ? (
        <>
          <CheckCircle2 className="h-4 w-4 text-fulkro-success" strokeWidth={2.3} />
          <span className="font-medium">audit_log integridad: OK</span>
          <TooltipENS text="Hash chain SHA-256 íntegro · R6 inviolable preservada · evidencia ENAC NO comprometida." />
        </>
      ) : (
        <>
          <AlertTriangle className="h-4 w-4 text-fulkro-danger" strokeWidth={2.3} />
          <span className="font-medium">audit_log integridad: FALLO</span>
          {firstBadSeq !== null && (
            <span className="text-xs text-fulkro-danger">
              (primer seq corrupto: {firstBadSeq})
            </span>
          )}
        </>
      )}
    </div>
  );
}

function PdfMetadataRow({ report }: { report: SimulacroReport }) {
  return (
    <div className="rounded-md bg-muted p-3 text-xs space-y-1">
      <p>
        <span className="font-medium">PDF SHA-256:</span>{" "}
        <code className="font-mono">{report.pdf_sha256.slice(0, 16)}...</code>
      </p>
      <p>
        <span className="font-medium">Tamaño:</span> {report.pdf_size_bytes} bytes
      </p>
      <p>
        <span className="font-medium">Firmado en:</span>{" "}
        {format(new Date(report.signed_at), "PPp", { locale: es })}
      </p>
      <p>
        <span className="font-medium">Fase actual workflow:</span> {report.current_phase}
      </p>
    </div>
  );
}

interface MetricProps {
  label: string;
  value: number | string;
  tone: "default" | "success" | "warning" | "danger";
}

function Metric({ label, value, tone }: MetricProps) {
  const colorClass =
    tone === "success"
      ? "text-fulkro-success"
      : tone === "warning"
        ? "text-fulkro-warning"
        : tone === "danger"
          ? "text-fulkro-danger"
          : "";
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
    </div>
  );
}
