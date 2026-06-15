"use client";

/**
 * /admin/system-health · Admin UI Bloque 4 Phase D v3.12.
 *
 * Self-monitoring FULKRO platform single pane of glass admin internal.
 * Combines:
 *   - 19 compliance checks m_compliance_monitor latest status
 *   - LLM anomaly alerts count m_observability
 *   - DB connection basic health
 *
 * Refetch automatic 60s · admin-only.
 */
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  HelpCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { api } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type HealthIndicator = "ok" | "warning" | "critical" | "unknown";

interface CheckHealth {
  name: string;
  description: string | null;
  status: HealthIndicator;
  last_run_at: string | null;
  severity: string | null;
  frequency: string | null;
}

interface SystemHealthResponse {
  generated_at: string;
  overall_health: HealthIndicator;
  counts: Record<string, number>;
  compliance_checks: CheckHealth[];
  llm_anomalies_count: number;
  db_connection_ok: boolean;
}

const HEALTH_LABELS: Record<HealthIndicator, string> = {
  ok: "OK",
  warning: "Atención",
  critical: "Crítico",
  unknown: "Sin datos",
};

const HEALTH_VARIANTS: Record<HealthIndicator, "success" | "warning" | "danger" | "outline"> = {
  ok: "success",
  warning: "warning",
  critical: "danger",
  unknown: "outline",
};

function StatusIcon({ status }: { status: HealthIndicator }) {
  if (status === "ok") return <CheckCircle2 className="h-4 w-4 text-emerald-700" />;
  if (status === "warning") return <AlertCircle className="h-4 w-4 text-amber-600" />;
  if (status === "critical") return <AlertCircle className="h-4 w-4 text-rose-600" />;
  return <HelpCircle className="h-4 w-4 text-slate-600" />;
}

function formatDateShort(iso: string | null): string {
  if (!iso) return "Sin runs";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function SystemHealthPage() {
  const query = useQuery<SystemHealthResponse>({
    queryKey: ["admin", "system-health"],
    queryFn: () => api<SystemHealthResponse>("/api/v1/admin/system-health"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const data = query.data;

  return (
    <div className="mx-auto space-y-6 max-w-6xl">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-indigo-600" />
          System Health · FULKRO platform
        </h1>
        <p className="text-sm text-muted-foreground">
          Self-monitoring FULKRO interno · 19 compliance checks autónomos +
          LLM anomalías + DB. Admin-only (cliente NO ve).
        </p>
      </header>

      {query.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : query.isError ? (
        <Alert variant="danger">
          <AlertTitle>Error cargando system health</AlertTitle>
          <AlertDescription>
            {(query.error as Error)?.message ?? "Error desconocido."}
          </AlertDescription>
        </Alert>
      ) : data ? (
        <>
          {/* Overall + KPI cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3" data-testid="kpi-cards">
            <Card data-testid="overall-card">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  Overall
                </CardTitle>
                <Badge variant={HEALTH_VARIANTS[data.overall_health]}>
                  {HEALTH_LABELS[data.overall_health]}
                </Badge>
              </CardHeader>
              <CardContent className="text-2xl font-bold">
                {data.compliance_checks.length}
                <span className="text-xs font-normal text-muted-foreground ml-1">
                  checks
                </span>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  Críticos
                </CardTitle>
                <AlertCircle className="h-4 w-4 text-rose-600" />
              </CardHeader>
              <CardContent className="text-2xl font-bold text-rose-700">
                {data.counts["critical"] ?? 0}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  LLM anomalías
                </CardTitle>
                <Sparkles className="h-4 w-4 text-amber-600" />
              </CardHeader>
              <CardContent className="text-2xl font-bold">
                {data.llm_anomalies_count}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                  DB
                </CardTitle>
                <Database
                  className={
                    data.db_connection_ok
                      ? "h-4 w-4 text-emerald-700"
                      : "h-4 w-4 text-rose-600"
                  }
                />
              </CardHeader>
              <CardContent className="text-base font-bold">
                {data.db_connection_ok ? "Conectado" : "Sin conexión"}
              </CardContent>
            </Card>
          </div>

          {/* Checks table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Compliance checks (m_compliance_monitor)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.compliance_checks.length === 0 ? (
                <p className="text-sm text-muted-foreground italic py-4">
                  Sin checks registrados todavía · ejecuta sync-registry.
                </p>
              ) : (
                <div
                  className="space-y-1"
                  data-testid="checks-list"
                >
                  {data.compliance_checks.map((c) => (
                    <div
                      key={c.name}
                      className="flex items-center gap-3 py-2 border-b border-border last:border-0"
                      data-testid="check-row"
                      data-check-name={c.name}
                    >
                      <StatusIcon status={c.status} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono">{c.name}</code>
                          <Badge
                            variant={HEALTH_VARIANTS[c.status]}
                            className="text-[10px]"
                          >
                            {HEALTH_LABELS[c.status]}
                          </Badge>
                          {c.frequency && (
                            <Badge variant="outline" className="text-[10px]">
                              {c.frequency}
                            </Badge>
                          )}
                        </div>
                        {c.description && (
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {c.description}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {formatDateShort(c.last_run_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <p className="text-xs text-muted-foreground text-right">
            Actualizado · {new Date(data.generated_at).toLocaleString("es-ES")}
          </p>
        </>
      ) : null}
    </div>
  );
}
