"use client";

import {
  Activity,
  ArrowDownCircle,
  ArrowRightCircle,
  ArrowUpCircle,
  Clock,
  Loader2,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { useDelta, useScore, useVerificationRuns } from "@/hooks/useVerification";
import type { SecurityScore, Trend } from "@/lib/verification-types";
import { cn, formatDate } from "@/lib/utils";

const LEVEL_STYLES: Record<SecurityScore["level"], { bg: string; text: string; label: string }> = {
  excelente:   { bg: "bg-fulkro-success/10",  text: "text-fulkro-success",   label: "Excelente" },
  aceptable:   { bg: "bg-fulkro-info/10", text: "text-fulkro-info", label: "Aceptable" },
  mejorable:   { bg: "bg-fulkro-warning/10",  text: "text-fulkro-warning",   label: "Mejorable" },
  critico:     { bg: "bg-fulkro-danger/10",    text: "text-fulkro-danger",     label: "Crítico" },
  bloqueante:  { bg: "bg-fulkro-danger/20",    text: "text-fulkro-danger",     label: "Bloqueante" },
};

const TREND_STYLES: Record<Trend, { icon: typeof TrendingUp; text: string; label: string }> = {
  mejorando:  { icon: TrendingUp,   text: "text-fulkro-success", label: "Mejorando" },
  estable:    { icon: ArrowRightCircle, text: "text-fulkro-info", label: "Estable" },
  empeorando: { icon: TrendingDown, text: "text-fulkro-danger",  label: "Empeorando" },
};

export function SecurityScoreHeader({ projectId }: { projectId: string }) {
  const score = useScore(projectId);
  const delta = useDelta(projectId);
  const runs = useVerificationRuns(projectId);

  if (score.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center gap-2 p-6 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={14} className="animate-spin" /> calculando puntuación…
        </CardContent>
      </Card>
    );
  }

  if (score.error) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          No se pudo obtener la puntuación: {(score.error as Error).message}
        </CardContent>
      </Card>
    );
  }

  const current = score.data?.current;
  const level = current?.level ?? "mejorable";
  const levelStyle = LEVEL_STYLES[level];
  const trendVal: Trend = delta.data?.overall_trend ?? "estable";
  const trendStyle = TREND_STYLES[trendVal];
  const TrendIcon = trendStyle.icon;

  const runsList = runs.data?.runs ?? [];
  const lastCompleted = runsList.find((r) => r.status === "completed");
  const scheduled = runsList.find((r) => r.status === "pending" || r.status === "scheduled");

  return (
    <Card>
      <CardContent className="grid gap-4 p-6 md:grid-cols-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            <ShieldCheck size={12} /> Puntuación de seguridad
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-5xl font-semibold text-fulkro-primary-700">
              {current?.score ?? "—"}
            </span>
            <span className="text-lg text-fulkro-ink-500">/ 100</span>
          </div>
          <span
            className={cn(
              "inline-flex w-fit items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
              levelStyle.bg,
              levelStyle.text,
            )}
          >
            {levelStyle.label}
          </span>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            <Activity size={12} /> Hallazgos abiertos
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <SeverityBadge label="crítico" count={current?.critical ?? 0} color="bg-fulkro-danger text-white" />
            <SeverityBadge label="alto" count={current?.high ?? 0} color="bg-fulkro-danger-500 text-white" />
            <SeverityBadge label="medio" count={current?.medium ?? 0} color="bg-fulkro-warning text-white" />
            <SeverityBadge label="bajo" count={current?.low ?? 0} color="bg-fulkro-info text-white" />
          </div>
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Penalización total: {current?.total_penalty ?? 0} puntos
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            <TrendIcon size={12} /> Tendencia vs anterior
          </div>
          <span className={cn("text-xl font-semibold", trendStyle.text)}>
            {trendStyle.label}
          </span>
          <div className="flex flex-wrap gap-3 text-sm font-medium text-[color:var(--fulkro-muted)]">
            <span className="flex items-center gap-1">
              <ArrowUpCircle size={12} className="text-fulkro-danger" />
              <span className="font-semibold">{delta.data?.totals.new ?? 0}</span> nuevos
            </span>
            <span className="flex items-center gap-1">
              <ArrowDownCircle size={12} className="text-fulkro-success" />
              <span className="font-semibold">{delta.data?.totals.resolved ?? 0}</span> resueltos
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-1 text-sm">
          <div className="flex items-center gap-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            <Clock size={12} /> Cronograma
          </div>
          <div>
            <span className="text-fulkro-ink-500">Último scan:</span>{" "}
            <span className="font-medium text-fulkro-primary-700">
              {lastCompleted?.completed_at
                ? formatDate(lastCompleted.completed_at)
                : "sin ejecutar"}
            </span>
          </div>
          <div>
            <span className="text-fulkro-ink-500">Próximo:</span>{" "}
            <span className="font-medium text-fulkro-primary-700">
              {scheduled?.scheduled_start
                ? formatDate(scheduled.scheduled_start)
                : "no programado"}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SeverityBadge({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
        color,
      )}
      aria-label={`${count} hallazgos de severidad ${label}`}
    >
      <span>{count}</span>
      <span>{label}</span>
    </span>
  );
}
