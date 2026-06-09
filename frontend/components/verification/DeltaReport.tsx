"use client";

/**
 * NOTA: Recharts no soporta CSS variables en props fill/stroke.
 * Los valores hex de este archivo deben mantenerse sincronizados con
 * frontend/styles/tokens.css cuando los tokens cambien.
 *
 * Mapping actual:
 * #6e6e7a → --fulkro-ink-500   (axis ticks)
 * #b8b8c4 → --fulkro-ink-300   (axis lines)
 * #5048cc → --fulkro-primary-700 (bar fill principal)
 *
 * Si actualizas tokens.css, busca con grep estos hex en este archivo
 * y actualízalos también.
 */

import {
  ArrowDownCircle,
  ArrowRightCircle,
  ArrowUpCircle,
  Loader2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDelta, useScore } from "@/hooks/useVerification";
import type { Trend } from "@/lib/verification-types";
import { cn, formatDate } from "@/lib/utils";

const TREND_STYLES: Record<Trend, { icon: typeof TrendingUp; color: string; label: string }> = {
  mejorando: { icon: TrendingUp, color: "text-fulkro-success", label: "Mejorando" },
  estable: { icon: ArrowRightCircle, color: "text-fulkro-info", label: "Estable" },
  empeorando: { icon: TrendingDown, color: "text-fulkro-danger", label: "Empeorando" },
};

export function DeltaReport({ projectId }: { projectId: string }) {
  const delta = useDelta(projectId);
  const score = useScore(projectId);

  if (delta.isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Δ Delta vs run anterior</CardTitle>
        </CardHeader>
        <CardContent className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={14} className="animate-spin" /> calculando delta…
        </CardContent>
      </Card>
    );
  }

  if (delta.error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Δ Delta vs run anterior</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          Error: {(delta.error as Error).message}
        </CardContent>
      </Card>
    );
  }

  const data = delta.data!;
  const TrendIcon = TREND_STYLES[data.overall_trend].icon;
  const history = (score.data?.history ?? []).map((h, i) => ({
    idx: i,
    score: h.score ?? 0,
    date: h.completed_at ? formatDate(h.completed_at) : "",
  }));

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Δ Delta vs run anterior</CardTitle>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
              TREND_STYLES[data.overall_trend].color,
            )}
          >
            <TrendIcon size={12} /> {TREND_STYLES[data.overall_trend].label}
          </span>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-3">
        <DeltaCard
          icon={<ArrowUpCircle size={14} className="text-fulkro-danger" />}
          title="Nuevos"
          value={data.totals.new}
          items={data.new.slice(0, 5).map((f) => f.title)}
        />
        <DeltaCard
          icon={<ArrowDownCircle size={14} className="text-fulkro-success" />}
          title="Resueltos"
          value={data.totals.resolved}
          items={data.resolved.slice(0, 5).map((f) => f.title)}
        />
        <DeltaCard
          icon={<ArrowRightCircle size={14} className="text-fulkro-info" />}
          title="Persistentes"
          value={data.totals.persistent}
          items={data.persistent.slice(0, 5).map((f) => f.title)}
        />

        {history.length >= 2 && (
          <div className="md:col-span-3">
            <p className="mb-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Histórico puntuación · últimos {history.length} runs
            </p>
            <div className="h-40 w-full">
              <ResponsiveContainer>
                <BarChart data={history}>
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "#6e6e7a" /* ink-500 */ }}
                    axisLine={{ stroke: "#b8b8c4" /* ink-300 */ }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 10, fill: "#6e6e7a" /* ink-500 */ }}
                    axisLine={{ stroke: "#b8b8c4" /* ink-300 */ }}
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 12 }}
                    formatter={(v: number) => [`${v}/100`, "score"]}
                  />
                  <Bar
                    dataKey="score"
                    fill="#5048cc" /* primary-700 */
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DeltaCard({
  icon,
  title,
  value,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  value: number;
  items: string[];
}) {
  return (
    <div className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] bg-fulkro-ink-100/30 p-3">
      <div className="flex items-center gap-2 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {icon} {title}
      </div>
      <p className="mt-1 text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">{value}</p>
      {items.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
          {items.map((t, i) => (
            <li key={`${title}-${i}`} className="truncate">
              · {t}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
