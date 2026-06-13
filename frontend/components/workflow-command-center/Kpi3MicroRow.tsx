/**
 * Kpi3MicroRow · KPI cards micro · sub-atom 1.C.D.B.2 v3.8.
 *
 * 3 KPI cards micro: dims_captured · completed_count · proximo_hito.
 */
"use client";

import { CheckCircle2, Compass, Hourglass } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface Kpi3MicroRowProps {
  dimsCaptured: number;
  dimsTotal: number;
  completedCount: number;
  totalCount: number;
  proximoHitoDays: number | null;
}

export function Kpi3MicroRow({
  dimsCaptured,
  dimsTotal,
  completedCount,
  totalCount,
  proximoHitoDays,
}: Kpi3MicroRowProps) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
      <KpiCard
        icon={<Compass className="size-4" />}
        label="Dimensiones"
        value={`${dimsCaptured}/${dimsTotal}`}
        accent="primary"
      />
      <KpiCard
        icon={<CheckCircle2 className="size-4" />}
        label="Completado"
        value={`${completedCount}/${totalCount}`}
        accent="emerald"
      />
      <KpiCard
        icon={<Hourglass className="size-4" />}
        label="Próximo hito"
        value={proximoHitoDays === null ? "—" : `${proximoHitoDays}d`}
        accent="amber"
      />
    </div>
  );
}

function KpiCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent: "primary" | "emerald" | "amber";
}) {
  const accentClasses: Record<typeof accent, string> = {
    primary: "text-primary",
    emerald: "text-emerald-700",
    amber: "text-amber-600",
  };
  return (
    <Card>
      <CardContent className="py-3 px-3">
        <div className="flex items-center gap-2">
          <span className={accentClasses[accent]}>{icon}</span>
          <div className="min-w-0">
            <p className="text-[10px] uppercase font-semibold text-foreground/70 tracking-wide">
              {label}
            </p>
            <p className="text-lg font-semibold tabular-nums leading-tight">
              {value}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
