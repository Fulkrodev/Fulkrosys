"use client";

/**
 * AuditDryRunDashboard · home dry-run pre-auditoría externa
 * (ADR-037 SAN-D MB-15.4). Orchestrator M10 (58 preguntas
 * deterministas L0-L5) + A11 (senior layer PAC + sectorial +
 * narrativa).
 *
 * Coherencia visual ADR-035 + TRAD-9 ADR-036:
 * - shadcn Card · Badge · Button · Progress · Skeleton composition
 * - fulkro-success/warning/danger palette (NO hex hardcoded)
 * - lucide-react icons (PlayCircle · Loader2 · History · etc)
 * - 0 TODO/FIXME inline
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  History,
  Loader2,
  PlayCircle,
} from "lucide-react";
import { useState } from "react";

import { A11SeniorLayerCard } from "@/components/audit-dry-run/A11SeniorLayerCard";
import { GapAnalysisCard } from "@/components/audit-dry-run/GapAnalysisCard";
import { M10FindingsTable } from "@/components/audit-dry-run/M10FindingsTable";
import { SimulacroPreEnacTab } from "@/components/audit-dry-run/SimulacroPreEnacTab";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { auditDryRunApi, type DryRunResult } from "@/lib/api/audit-dry-run";

interface Props {
  projectId: string;
}

export function AuditDryRunDashboard({ projectId }: Props) {
  const queryClient = useQueryClient();
  const [latestResult, setLatestResult] = useState<DryRunResult | null>(null);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["audit-dry-run-summary", projectId],
    queryFn: () => auditDryRunApi.getSummary(projectId),
    staleTime: 30_000,
  });

  const executeMutation = useMutation({
    mutationFn: () => auditDryRunApi.execute(projectId),
    onSuccess: (data) => {
      setLatestResult(data);
      queryClient.invalidateQueries({
        queryKey: ["audit-dry-run-summary", projectId],
      });
    },
  });

  const isExecuting = executeMutation.isPending;
  const lastExecuted = summary?.last_executed_at;

  return (
    <Tabs defaultValue="dry-run" className="space-y-6">
      <TabsList className="grid w-full max-w-md grid-cols-2" data-testid="audit-prep-tabs-list">
        <TabsTrigger value="dry-run" data-testid="audit-prep-tab-dry-run">
          Dry-Run M10+A11
        </TabsTrigger>
        <TabsTrigger value="simulacro-pre-enac" data-testid="audit-prep-tab-simulacro">
          Simulacro Pre-ENAC
        </TabsTrigger>
      </TabsList>

      <TabsContent value="dry-run" className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="h-5 w-5 text-fulkro-info" strokeWidth={2.3} />
            Dry-Run pre-auditoría · M10 + A11 senior
          </CardTitle>
          <CardDescription>
            M10 evalúa 58 preguntas ENAC determinísticas L0-L5 contra
            evidencia real · A11 añade PAC sector-aware + preguntas
            sectoriales + narrativa ejecutiva. Tiempo esperado 30-90s.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {summaryLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : lastExecuted ? (
            <div className="rounded-md bg-muted p-3 text-sm">
              <p className="font-medium">Última ejecución:</p>
              <p className="text-muted-foreground">
                {format(new Date(lastExecuted), "PPp", { locale: es })}
                {" · Score: "}
                <strong>{summary?.overall_readiness_score}%</strong>
                {" · Gaps: "}
                <strong>{summary?.gaps_detected}</strong>
                {summary && summary.critical_gaps > 0 && (
                  <span className="ml-2 text-fulkro-danger">
                    · {summary.critical_gaps} críticos
                  </span>
                )}
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Sin ejecuciones previas. Ejecuta dry-run para detectar gaps
              antes de auditoría externa.
            </p>
          )}

          <Button
            onClick={() => executeMutation.mutate()}
            disabled={isExecuting}
            size="lg"
          >
            {isExecuting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={2.3} />
                Ejecutando dry-run · M10 + A11...
              </>
            ) : (
              <>
                <PlayCircle className="mr-2 h-4 w-4" strokeWidth={2.3} />
                Ejecutar Dry-Run completo
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {latestResult && <ResultDisplay result={latestResult} />}

      {summary && summary.history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="h-4 w-4" strokeWidth={2.3} />
              Histórico ({summary.history.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {summary.history.map((h) => (
                <li
                  key={h.id}
                  className="flex items-center justify-between rounded border p-2 text-sm"
                >
                  <span className="text-muted-foreground">
                    {format(new Date(h.executed_at), "PPp", { locale: es })}
                  </span>
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={h.score >= 80 ? "success" : "warning"}
                    >
                      {h.score}%
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {h.gaps} gaps
                      {h.critical_gaps > 0 && (
                        <span className="ml-1 text-fulkro-danger">
                          ({h.critical_gaps} críticos)
                        </span>
                      )}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
      </TabsContent>

      <TabsContent value="simulacro-pre-enac" className="space-y-6">
        <SimulacroPreEnacTab projectId={projectId} />
      </TabsContent>
    </Tabs>
  );
}

function ResultDisplay({ result }: { result: DryRunResult }) {
  const score = result.overall_readiness_score;
  const progressColor =
    score >= 80 ? "success" : score >= 60 ? "warning" : "danger";

  return (
    <div className="space-y-4">
      <Card className="border-l-4 border-l-fulkro-info">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>
              Dry-run{" "}
              <TooltipENS text="Auditoría preliminar interna · simula la auditoría ENAC oficial · te indica gaps antes de exponer al auditor real." />{" "}
              completado · {result.category_at_execution}
            </CardTitle>
            <Badge variant={score >= 80 ? "success" : "warning"}>
              {score}% madurez
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Metric
              label="Preguntas evaluadas"
              value={result.total_questions}
              tone="default"
            />
            <Metric
              label="Con evidencia"
              value={result.questions_with_evidence}
              tone="success"
            />
            <Metric
              label="Gaps detectados"
              value={result.gaps_detected}
              tone={result.critical_gaps > 0 ? "danger" : "warning"}
              hint={
                result.critical_gaps > 0
                  ? `${result.critical_gaps} críticos`
                  : undefined
              }
            />
          </div>

          <Progress value={score} color={progressColor} className="h-2" />
        </CardContent>
      </Card>

      {result.m10_summary && (
        <GapAnalysisCard findings={result.m10_summary.findings} />
      )}

      {result.a11_payload && (
        <A11SeniorLayerCard payload={result.a11_payload} />
      )}

      {result.m10_summary && (
        <M10FindingsTable findings={result.m10_summary.findings} />
      )}
    </div>
  );
}

interface MetricProps {
  label: string;
  value: number;
  tone: "default" | "success" | "warning" | "danger";
  hint?: string;
}

function Metric({ label, value, tone, hint }: MetricProps) {
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
      <p className={`text-2xl font-bold ${colorClass}`}>
        {value}
        {hint && (
          <span className="ml-2 text-xs font-medium text-fulkro-danger">
            ({hint})
          </span>
        )}
      </p>
    </div>
  );
}
