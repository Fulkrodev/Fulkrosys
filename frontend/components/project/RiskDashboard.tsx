/**
 * RiskDashboard · MAGERIT M02 risk overview (FASE 9.B / MB-4.C.4).
 *
 * Backend: GET /api/v1/projects/{project_id}/risk-overview composer
 * M02 magerit_risk_calculation + magerit_treatment_plan.
 *
 * Vista complementaria a /magerit (que tiene el detalle MAGERIT completo).
 * Aquí: distribución por risk_level, status de tratamientos, top 10 críticos.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Target,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { InfoTag } from "@/components/ui/info-tag";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

interface RiskOverviewResponse {
  total_risks: number;
  by_risk_level: {
    MC: number;
    C: number;
    I: number;
    A: number;
    D: number;
  };
  by_treatment: {
    pending: number;
    in_progress: number;
    completed: number;
  };
  top_critical: Array<{
    risk_calculation_id: string;
    asset_id: string;
    asset_name: string;
    threat_code: string;
    dimension: string;
    risk_level: string | null;
    risk_effective: number | null;
    risk_intrinsic_accumulated: number | null;
    treatment_status: string | null;
    treatment_decision: string | null;
  }>;
  analyses_count: number;
}

const RISK_LEVEL_LABEL: Record<string, string> = {
  MC: "Muy crítico",
  C: "Crítico",
  I: "Importante",
  A: "Aceptable",
  D: "Despreciable",
};

const RISK_LEVEL_TONE: Record<string, string> = {
  MC: "bg-red-600 text-white border-red-700",
  C: "bg-orange-500 text-white border-orange-600",
  I: "bg-amber-400 text-amber-950 border-amber-500",
  A: "bg-emerald-200 text-emerald-900 border-emerald-300",
  D: "bg-fulkro-ink-200 text-fulkro-ink-700 border-fulkro-ink-300",
};

const DIMENSION_LABEL: Record<string, string> = {
  D: "Disponibilidad",
  I: "Integridad",
  C: "Confidencialidad",
  A: "Autenticidad",
  T: "Trazabilidad",
};

export function RiskDashboard({ projectId }: { projectId: string }) {
  const { data, isLoading, isError, error, refetch, isRefetching } = useQuery<RiskOverviewResponse>({
    queryKey: ["project-composer", "risk-overview", projectId],
    queryFn: () =>
      api<RiskOverviewResponse>(
        `/api/v1/projects/${projectId}/risk-overview`,
      ),
    enabled: Boolean(projectId),
    staleTime: 60_000,
    retry: false,
  });

  // Sub-atom Sesión 3B-2B Phase A.1 · loading skeleton matching layout
  // (NOT generic spinner · KPI cards + distribution bars + top critical table)
  if (isLoading) {
    return (
      <div className="space-y-4" aria-busy data-testid="risk-dashboard-loading">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-48" />
            <Skeleton className="mt-2 h-3 w-72" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-8 w-full" />
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
          </CardHeader>
          <CardContent className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  // Sub-atom Sesión 3B-2B Phase A.1 · error retry button + technical detail.
  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="danger" className="flex flex-col gap-3">
            <div>
              <AlertTitle>No se pudo cargar la vista de riesgos</AlertTitle>
              <AlertDescription>
                {error instanceof Error ? error.message : "Error desconocido"}
              </AlertDescription>
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void refetch()}
              disabled={isRefetching}
              className="self-start"
              data-testid="risk-dashboard-retry"
            >
              <RefreshCw
                size={14}
                className={isRefetching ? "animate-spin" : ""}
              />
              Reintentar
            </Button>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (data.analyses_count === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <EmptyState
            title="Sin análisis MAGERIT"
            description="Cuando se ejecute el primer análisis MAGERIT (Motor 02) aparecerá la distribución de riesgos aquí."
          />
        </CardContent>
      </Card>
    );
  }

  const totalCritical = data.by_risk_level.MC + data.by_risk_level.C;
  const treatmentTotal =
    data.by_treatment.pending +
    data.by_treatment.in_progress +
    data.by_treatment.completed;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlert size={16} /> Vista de riesgos (
            <InfoTag term="MAGERIT" display="MAGERIT" /> M02)
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            {data.analyses_count} análisis · {data.total_risks} cálculos · vista
            complementaria al detalle en pestaña MAGERIT
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-fulkro-ink-500">
              Distribución por nivel
            </p>
            <RiskLevelBars data={data.by_risk_level} total={data.total_risks} />
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <Stat
              label="Críticos abiertos"
              value={String(totalCritical)}
              icon={<AlertTriangle size={11} className="text-red-600" />}
              tone={totalCritical > 0 ? "danger" : "success"}
            />
            <Stat
              label="Treatments pendientes"
              value={String(data.by_treatment.pending)}
              icon={<Target size={11} />}
              tone={data.by_treatment.pending > 0 ? "warning" : "success"}
              meta={
                treatmentTotal > 0
                  ? `${data.by_treatment.completed}/${treatmentTotal} completados`
                  : null
              }
            />
            <Stat
              label="Total análisis"
              value={String(data.analyses_count)}
              icon={<ShieldCheck size={11} />}
              meta="MAGERIT runs activos"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Top críticos abiertos</CardTitle>
        </CardHeader>
        <CardContent>
          {data.top_critical.length === 0 ? (
            <p className="text-xs text-fulkro-ink-500">
              No hay riesgos críticos (MC/C) abiertos. Excelente.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {data.top_critical.map((r) => (
                <CriticalRiskRow key={r.risk_calculation_id} risk={r} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RiskLevelBars({
  data,
  total,
}: {
  data: RiskOverviewResponse["by_risk_level"];
  total: number;
}) {
  const levels = ["MC", "C", "I", "A", "D"] as const;
  const max = Math.max(1, ...levels.map((l) => data[l]));

  return (
    <div className="space-y-1.5">
      {levels.map((level) => {
        const count = data[level];
        const widthPct = (count / max) * 100;
        const sharePct = total > 0 ? (count / total) * 100 : 0;
        return (
          <div
            key={level}
            className="grid grid-cols-12 items-center gap-2 text-[11px]"
          >
            <div className="col-span-3">
              <Badge
                variant="outline"
                className={`${RISK_LEVEL_TONE[level]} font-mono`}
              >
                {level}
              </Badge>
              <span className="ml-1 text-fulkro-ink-700">
                {RISK_LEVEL_LABEL[level]}
              </span>
            </div>
            <div className="col-span-7">
              <div className="h-3 w-full rounded bg-fulkro-ink-100">
                <div
                  className="h-3 rounded bg-fulkro-primary-700"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
            <div className="col-span-2 text-right">
              <span className="font-mono text-fulkro-ink-700">{count}</span>
              <span className="ml-1 text-fulkro-ink-500">
                ({sharePct.toFixed(0)}%)
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CriticalRiskRow({
  risk,
}: {
  risk: RiskOverviewResponse["top_critical"][number];
}) {
  const tone =
    risk.risk_level === "MC" ? RISK_LEVEL_TONE.MC : RISK_LEVEL_TONE.C;
  return (
    <li className="flex items-start justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-2 text-xs">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {risk.asset_name}
        </p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 font-mono text-[10px] text-fulkro-ink-500">
          <span>{risk.threat_code}</span>
          <span>· {DIMENSION_LABEL[risk.dimension] ?? risk.dimension}</span>
          {risk.risk_effective !== null ? (
            <span>· efectivo {risk.risk_effective.toFixed(2)}</span>
          ) : null}
        </p>
        {risk.treatment_decision ? (
          <p className="mt-0.5 text-[10px] text-fulkro-ink-500">
            Tratamiento: {risk.treatment_decision}
          </p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        {risk.risk_level ? (
          <Badge variant="outline" className={`${tone} font-mono`}>
            {risk.risk_level}
          </Badge>
        ) : null}
        {risk.treatment_status ? (
          <Badge variant="secondary" className="text-[10px]">
            {risk.treatment_status}
          </Badge>
        ) : null}
      </div>
    </li>
  );
}

function Stat({
  label,
  value,
  meta,
  icon,
  tone = "default",
}: {
  label: string;
  value: string;
  meta?: string | null;
  icon?: React.ReactNode;
  tone?: "default" | "warning" | "danger" | "success";
}) {
  const toneCls =
    tone === "danger"
      ? "border-red-300 bg-red-50/50"
      : tone === "warning"
      ? "border-amber-300 bg-amber-50/50"
      : tone === "success"
      ? "border-emerald-300 bg-emerald-50/40"
      : "border-fulkro-ink-300/60 bg-white";
  return (
    <div className={`rounded-md border p-3 ${toneCls}`}>
      <p className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 truncate text-base font-semibold text-fulkro-ink-700">
        {value}
      </p>
      {meta ? (
        <p className="mt-0.5 truncate text-[11px] text-fulkro-ink-500">
          {meta}
        </p>
      ) : null}
    </div>
  );
}
