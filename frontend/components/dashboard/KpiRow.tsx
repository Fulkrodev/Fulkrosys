"use client";

import {
  Briefcase,
  FolderOpen,
  TrendingUp,
  Wallet,
} from "lucide-react";

import { KPICard } from "@/components/data/KPICard";
import { useDashboardKpis } from "@/hooks/useDashboardData";

function formatEuros(v: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(v);
}

export function KpiRow() {
  const { data, isLoading } = useDashboardKpis();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-[112px] animate-pulse rounded-lg border border-fulkro-ink-300/60 bg-fulkro-ink-100/40"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KPICard
        icon={FolderOpen}
        title="Proyectos activos"
        value={String(data.active_projects)}
        rag={data.projects_rag}
        subtitle="Dentro de plazo"
      />
      <KPICard
        icon={TrendingUp}
        title="Leads en pipeline"
        value={String(data.leads_count)}
        subtitle={formatEuros(data.leads_value_eur)}
      />
      <KPICard
        icon={Briefcase}
        title="Retainers activos"
        value={String(data.retainers_active)}
        subtitle={`MRR ${formatEuros(data.mrr_eur)}`}
      />
      <KPICard
        icon={Wallet}
        title="Tesorería 30d"
        value={formatEuros(data.treasury_30d_eur)}
        trend={{
          direction: data.treasury_trend_pct >= 0 ? "up" : "down",
          pct: Math.abs(data.treasury_trend_pct),
        }}
        subtitle="vs. mes anterior"
      />
    </div>
  );
}
