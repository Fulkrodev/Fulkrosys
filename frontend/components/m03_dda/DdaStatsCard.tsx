/**
 * DdaStatsCard · KPIs DdA · sub-atom 1.D.F.A v3.11.
 *
 * Render cards KPI principal:
 *   - Total medidas Anexo II (73)
 *   - Aplicables / No aplica
 *   - Implantadas / Parcial / No implantadas / No valoradas
 *   - Completion percentage barra
 */
"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  CircleDot,
  ListChecks,
  Loader2,
  ShieldOff,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

import { useDdaAdminStats } from "@/hooks/useDdaAdmin";

interface DdaStatsCardProps {
  projectId: string;
}

export function DdaStatsCard({ projectId }: DdaStatsCardProps) {
  const { data, isLoading, isError, error } = useDdaAdminStats(projectId);

  if (isLoading) {
    return (
      <Card data-testid="dda-stats-loading">
        <CardContent className="py-6">
          <div className="flex items-center gap-2 text-sm text-foreground/70">
            <Loader2 className="size-4 animate-spin" />
            Cargando estadísticas DdA…
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card data-testid="dda-stats-error">
        <CardContent className="py-6 space-y-2">
          <p className="font-medium text-sm">
            No se pudieron cargar las estadísticas
          </p>
          <p className="text-xs text-foreground/70">
            {error instanceof Error ? error.message : "Error desconocido"}
          </p>
        </CardContent>
      </Card>
    );
  }

  const pct = Math.round(data.completion_pct);

  return (
    <div className="space-y-4" data-testid="dda-stats">
      {/* Completion */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ListChecks className="size-4 text-primary" />
            Progreso DdA · Anexo II
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold">{pct}%</span>
            <span className="text-xs text-foreground/70">
              {data.implantadas + data.parcial} de {data.total_aplicables}{" "}
              aplicables
            </span>
          </div>
          <Progress value={pct} className="h-2" />
        </CardContent>
      </Card>

      {/* Breakdown grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard
          label="Total medidas"
          value={data.total_medidas}
          icon={<ListChecks className="size-3.5" />}
          variant="default"
        />
        <KpiCard
          label="Aplicables"
          value={data.total_aplicables}
          icon={<Circle className="size-3.5" />}
          variant="info"
        />
        <KpiCard
          label="No aplica"
          value={data.no_aplica}
          icon={<ShieldOff className="size-3.5" />}
          variant="default"
        />
        <KpiCard
          label="Implantadas"
          value={data.implantadas}
          icon={<CheckCircle2 className="size-3.5" />}
          variant="success"
        />
        <KpiCard
          label="Parcial"
          value={data.parcial}
          icon={<CircleDot className="size-3.5" />}
          variant="info"
        />
        <KpiCard
          label="No implantadas"
          value={data.no_implantadas}
          icon={<AlertTriangle className="size-3.5" />}
          variant="danger"
        />
        <KpiCard
          label="No valoradas"
          value={data.no_valoradas}
          icon={<Circle className="size-3.5" />}
          variant="default"
        />
      </div>
    </div>
  );
}

interface KpiCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  variant: "default" | "info" | "success" | "danger";
}

function KpiCard({ label, value, icon, variant }: KpiCardProps) {
  const variantClasses: Record<KpiCardProps["variant"], string> = {
    default: "text-foreground/70",
    info: "text-blue-600",
    success: "text-emerald-700",
    danger: "text-red-600",
  };
  return (
    <Card className="border" data-testid={`dda-kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <CardContent className="py-3 px-3 space-y-1">
        <div
          className={`flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide ${variantClasses[variant]}`}
        >
          {icon}
          <span>{label}</span>
        </div>
        <p className="text-xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
