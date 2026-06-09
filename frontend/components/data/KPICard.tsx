import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { RagStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface KPICardProps {
  icon?: LucideIcon;
  title: string;
  value: string;
  subtitle?: string;
  trend?: { direction: "up" | "down" | "flat"; pct: number };
  rag?: RagStatus;
  className?: string;
}

// Sub-atom Sesión 3B-2B.2 Phase A.1 · WCAG color-contrast fix.
// Empirical on white card bg (post Card.tsx bg fix):
//   text-fulkro-success (44,140,92) → 3.87:1 ratio (FAIL AA)
//   text-fulkro-danger (179,74,60) → 5.44:1 (PASSES but inconsistent with success)
// -700 shades:
//   text-fulkro-success-700 (30,95,63) → ~7:1 (AAA)
//   text-fulkro-danger-700 (122,50,41) → ~10.5:1 (AAA)
// flat omitted from render branch (direction!=="flat" gate) so kept as-is.
const TREND_COLORS = {
  up: "text-fulkro-success-700",
  down: "text-fulkro-danger-700",
  flat: "text-fulkro-ink-500",
};

export function KPICard({
  icon: Icon,
  title,
  value,
  subtitle,
  trend,
  rag,
  className,
}: KPICardProps) {
  return (
    <Card className={cn("h-full", className)}>
      <CardContent className="flex items-start justify-between gap-3 p-6 pt-6">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              {title}
            </p>
            {rag && (
              <span className={cn("rag-dot", `rag-dot-${rag}`)} aria-hidden />
            )}
          </div>
          <p className="mt-2 text-4xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
            {value}
          </p>
          <div className="mt-1.5 flex items-center gap-2 text-sm">
            {trend && trend.direction !== "flat" && (
              <span
                className={cn(
                  "inline-flex items-center gap-0.5 font-bold",
                  TREND_COLORS[trend.direction],
                )}
              >
                {trend.direction === "up" ? (
                  <ArrowUpRight size={16} strokeWidth={2.4} />
                ) : (
                  <ArrowDownRight size={16} strokeWidth={2.4} />
                )}
                {trend.pct}%
              </span>
            )}
            {subtitle && (
              <span className="font-medium text-[color:var(--fulkro-muted)]">
                {subtitle}
              </span>
            )}
          </div>
        </div>
        {Icon && (
          <span
            style={{
              backgroundColor: "var(--fulkro-surface-glass-strong)",
              color: "var(--fulkro-subtitle)",
            }}
            className="shrink-0 rounded-lg p-2.5"
          >
            <Icon size={22} strokeWidth={2.2} />
          </span>
        )}
      </CardContent>
    </Card>
  );
}
