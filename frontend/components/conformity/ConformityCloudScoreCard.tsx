"use client";

import * as React from "react";
import { Cloud, CloudOff, Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { useConformityCloudScore } from "@/hooks/useCloudConnectorsAdmin";
import type { FamiliaBreakdown } from "@/lib/api/cloud-connectors-admin";

export interface ConformityCloudScoreCardProps {
  projectId: string;
}

const FAMILIA_LABEL: Record<string, string> = {
  "op.acc": "Control de acceso",
  "op.exp": "Explotación",
  "op.cont": "Continuidad",
  "mp.s": "Servicios",
  "mp.info": "Información",
  org: "Organización",
};

// R29 firmísimo · NUNCA rojo · solo verde/ámbar/neutro (R30 score=0 graceful).
function toneFor(score: number): {
  bg: string;
  text: string;
  border: string;
  bar: string;
} {
  if (score >= 70) {
    return {
      bg: "bg-fulkro-success/10",
      text: "text-fulkro-success",
      border: "border-fulkro-success/30",
      bar: "bg-fulkro-success",
    };
  }
  if (score >= 30) {
    return {
      bg: "bg-fulkro-warning/10",
      text: "text-fulkro-warning",
      border: "border-fulkro-warning/30",
      bar: "bg-fulkro-warning",
    };
  }
  // Score bajo (0-29) · neutro · NUNCA rojo · NO presión
  return {
    bg: "bg-[color:var(--fulkro-surface-glass)]",
    text: "text-[color:var(--fulkro-subtitle)]",
    border: "border-[color:var(--fulkro-surface-glass-border)]",
    bar: "bg-fulkro-primary-500",
  };
}

function FamiliaBar({ item, palette }: { item: FamiliaBreakdown; palette: { bar: string } }) {
  const pct = item.total > 0 ? Math.round((item.verified / item.total) * 100) : 0;
  return (
    <div
      className="space-y-1"
      data-testid={`cloud-score-familia-${item.familia}`}
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">
          {FAMILIA_LABEL[item.familia] ?? item.familia}{" "}
          <span className="text-[color:var(--fulkro-subtitle)]">
            ({item.familia})
          </span>
        </span>
        <span className="font-mono">
          {item.verified}/{item.total}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[color:var(--fulkro-surface-glass)]">
        <div
          className={`h-full rounded-full ${palette.bar}`}
          style={{ width: `${pct}%` }}
          aria-label={`${pct}% verificación ${item.familia}`}
        />
      </div>
    </div>
  );
}

export function ConformityCloudScoreCard({
  projectId,
}: ConformityCloudScoreCardProps) {
  const { data, isLoading } = useConformityCloudScore(projectId);

  if (isLoading) {
    return (
      <Card data-testid="cloud-score-loading">
        <CardContent className="flex h-24 items-center justify-center">
          <Loader2 className="size-5 animate-spin text-fulkro-primary-500" />
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const { measures_cloud_verified, measures_total_aplicable, score_percentage } =
    data;
  const palette = toneFor(score_percentage);

  // Empty state · sin connectors o sin cobertura · R29 NO presión
  if (measures_total_aplicable === 0) {
    return null;
  }

  if (score_percentage === 0) {
    return (
      <Card data-testid="cloud-score-empty">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <CloudOff
              size={16}
              className="text-[color:var(--fulkro-subtitle)]"
            />
            Verificación cloud
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-sm text-[color:var(--fulkro-subtitle)]">
            Aún no hay medidas verificadas via cloud · todas vía documental
            ({measures_total_aplicable} medidas aplicables a esta categoría).
          </p>
          <p className="mt-2 text-xs text-[color:var(--fulkro-subtitle)]">
            Conecta un proveedor cloud (M365 · AWS · Azure · GCP) para empezar
            verificación automática.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      className={`border ${palette.border} ${palette.bg}`}
      data-testid="cloud-score-card"
    >
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Cloud size={16} className={palette.text} />
          Verificación cloud
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {/* Stats summary */}
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <div className="flex items-baseline gap-1">
              <span
                className={`text-2xl font-bold ${palette.text}`}
                data-testid="cloud-score-percentage"
              >
                {score_percentage.toFixed(1)}%
              </span>
              <span className="text-sm text-[color:var(--fulkro-subtitle)]">
                verificación cloud
              </span>
            </div>
            <p
              className="mt-1 text-xs text-[color:var(--fulkro-subtitle)]"
              data-testid="cloud-score-summary"
            >
              <span className="font-mono font-semibold">
                {measures_cloud_verified}/{measures_total_aplicable}
              </span>{" "}
              medidas verificadas via cloud · resto vía documental
            </p>
          </div>
        </div>

        {/* Familia breakdown bars */}
        {data.per_familia_breakdown.length > 0 && (
          <div className="space-y-2.5" data-testid="cloud-score-breakdown">
            {data.per_familia_breakdown.map((item) => (
              <FamiliaBar key={item.familia} item={item} palette={palette} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
