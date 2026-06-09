/**
 * ProjectSummary · 6 KPIs cross-motor (FASE 9.B / MB-4.C.2).
 *
 * Backend: GET /api/v1/projects/{project_id}/summary
 * KPIs: categoría ENS · fase · DdA stats · risks críticos · findings
 * abiertos · próxima certificación · estado conformidad.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarCheck,
  Loader2,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";

interface ProjectSummaryResponse {
  categoria_ens: string | null;
  fase: string;
  dda: {
    total: number;
    aplicables: number;
    no_aplica: number;
    pendientes_revision: number;
  };
  risks_critical_open: number;
  findings_open: number;
  fecha_objetivo_certificacion: string | null;
  conformity: {
    route_status: string | null;
    route_type: string | null;
    expiration_date: string | null;
    submissions_count: number;
    renewals_count: number;
    material_changes_count: number;
  };
}

export function ProjectSummaryView({ projectId }: { projectId: string }) {
  const { data, isLoading, isError, error } = useQuery<ProjectSummaryResponse>(
    {
      queryKey: ["project-composer", "summary", projectId],
      queryFn: () =>
        api<ProjectSummaryResponse>(`/api/v1/projects/${projectId}/summary`),
      enabled: Boolean(projectId),
      staleTime: 60_000,
      retry: false,
    },
  );

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> cargando resumen…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar el resumen</AlertTitle>
            <AlertDescription>
              {error instanceof Error ? error.message : "Error desconocido"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const dda = data.dda;
  const ddaPct = dda.total
    ? Math.round((100 * (dda.aplicables + dda.no_aplica)) / dda.total)
    : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp size={16} /> Resumen del proyecto
        </CardTitle>
        <p className="mt-1 text-xs text-fulkro-ink-500">
          KPIs cross-motor · M03 DdA · M02 riesgos · M08 findings · M27 conformidad
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Kpi
            label="Categoría ENS"
            icon={<ShieldCheck size={12} />}
            value={data.categoria_ens ?? "no fijada"}
            meta={`Fase: ${data.fase}`}
          />
          <Kpi
            label="DdA"
            icon={<ScrollText size={12} />}
            value={`${dda.aplicables} aplicables`}
            meta={`${dda.total} total · ${ddaPct}% revisada`}
            subValue={
              dda.pendientes_revision > 0
                ? `${dda.pendientes_revision} pendiente${dda.pendientes_revision !== 1 ? "s" : ""}`
                : null
            }
            tone={
              dda.pendientes_revision > 0 ? "warning" : "default"
            }
          />
          <Kpi
            label="Riesgos críticos"
            icon={<ShieldAlert size={12} />}
            value={String(data.risks_critical_open)}
            meta={
              data.risks_critical_open > 0
                ? "MC + C abiertos (MAGERIT)"
                : "Sin riesgos críticos abiertos"
            }
            tone={data.risks_critical_open > 0 ? "danger" : "success"}
          />
          <Kpi
            label="Findings abiertos"
            icon={<AlertTriangle size={12} />}
            value={String(data.findings_open)}
            meta="open + needs_review (M08)"
            tone={data.findings_open > 0 ? "warning" : "success"}
          />
          <Kpi
            label="Conformidad"
            icon={<ShieldCheck size={12} />}
            value={
              data.conformity.route_type ?? data.conformity.route_status ?? "—"
            }
            meta={
              data.conformity.expiration_date
                ? `expira ${new Date(data.conformity.expiration_date).toLocaleDateString()}`
                : `${data.conformity.submissions_count} submissions`
            }
          />
          <Kpi
            label="Certificación objetivo"
            icon={<CalendarCheck size={12} />}
            value={
              data.fecha_objetivo_certificacion
                ? new Date(data.fecha_objetivo_certificacion).toLocaleDateString()
                : "no fijada"
            }
            meta={
              data.fecha_objetivo_certificacion
                ? formatRelativeDays(data.fecha_objetivo_certificacion)
                : null
            }
          />
        </div>
      </CardContent>
    </Card>
  );
}

function formatRelativeDays(iso: string): string {
  const target = new Date(iso);
  const now = new Date();
  const diffDays = Math.round(
    (target.getTime() - now.getTime()) / (24 * 60 * 60 * 1000),
  );
  if (diffDays > 0) return `${diffDays} días`;
  if (diffDays < 0) return `vencido hace ${-diffDays} días`;
  return "hoy";
}

type KpiTone = "default" | "warning" | "danger" | "success";

const TONE_CLASSES: Record<KpiTone, string> = {
  default: "border-fulkro-ink-300/60 bg-white",
  warning: "border-amber-300 bg-amber-50/50",
  danger: "border-red-300 bg-red-50/50",
  success: "border-emerald-300 bg-emerald-50/40",
};

function Kpi({
  label,
  value,
  meta,
  subValue,
  icon,
  tone = "default",
}: {
  label: string;
  value: string;
  meta?: string | null;
  subValue?: string | null;
  icon?: React.ReactNode;
  tone?: KpiTone;
}) {
  return (
    <div className={`rounded-md border p-3 ${TONE_CLASSES[tone]}`}>
      <p className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
        {icon}
        {label}
      </p>
      <p className="mt-1 truncate text-base font-semibold text-fulkro-ink-700">
        {value}
      </p>
      {meta ? (
        <p className="mt-0.5 truncate text-[11px] text-fulkro-ink-500">
          {meta}
        </p>
      ) : null}
      {subValue ? (
        <Badge variant="warning" className="mt-1">
          {subValue}
        </Badge>
      ) : null}
    </div>
  );
}
