import type { RagStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Tiers reales del backend (Motor 23 paso 2). Aceptamos string para
 * tolerar tier_codes futuros sin romper el render.
 */
const PLAN_LABEL: Record<string, string> = {
  R_MICRO: "Micro",
  R_LITE: "Lite",
  R_STD: "Standard",
  R_PLUS: "Plus",
  R_CRITICAL: "Critical",
};

// Sub-atom Sesión 3B-2B.2 Phase A.3.X · WCAG color-contrast fix
// (Phase A.1 -700 rule extended to /20 tinted bg variants).
const PLAN_STYLES: Record<string, string> = {
  R_MICRO:
    "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-body)]",
  R_LITE:
    "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-body)]",
  R_STD: "bg-fulkro-primary-700/10 text-fulkro-primary-700",
  R_PLUS: "bg-fulkro-primary-500/20 text-fulkro-primary-700",
  R_CRITICAL: "bg-fulkro-danger/10 text-fulkro-danger-700",
};

const PLAN_FALLBACK_STYLE =
  "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-body)]";

export function RetainerPlanBadge({
  plan,
  feeEurMonth,
  className,
}: {
  plan: string;
  feeEurMonth?: number;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider",
        PLAN_STYLES[plan] ?? PLAN_FALLBACK_STYLE,
        className,
      )}
    >
      {PLAN_LABEL[plan] ?? plan}
      {typeof feeEurMonth === "number" && (
        // -700 ink shade for adequate contrast on /20 tinted parent bg.
        <span className="font-normal tracking-normal text-fulkro-ink-700">
          · {feeEurMonth}€/m
        </span>
      )}
    </span>
  );
}

export function DriftBadge({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const rag: RagStatus = score >= 2 ? "red" : score >= 1 ? "amber" : "green";
  // -700 shade for WCAG AA contrast on /10 tinted bg (Phase A.1 rule).
  const style =
    rag === "red"
      ? "bg-fulkro-danger/10 text-fulkro-danger-700"
      : rag === "amber"
        ? "bg-fulkro-warning/10 text-fulkro-warning-700"
        : "bg-fulkro-success/10 text-fulkro-success-700";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold",
        style,
        className,
      )}
      title="Drift = desviación acumulada entre última foto y estado actual"
    >
      Drift {score.toFixed(1)}
    </span>
  );
}

export function CapacityBar({
  consumedPct,
  className,
}: {
  consumedPct: number;
  className?: string;
}) {
  const clamped = Math.min(120, Math.max(0, consumedPct));
  const over = clamped > 100;
  const color =
    clamped > 100
      ? "bg-fulkro-danger"
      : clamped > 85
        ? "bg-fulkro-warning"
        : "bg-fulkro-primary-700";
  return (
    <div className={cn("flex items-center gap-2 text-xs", className)}>
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-fulkro-ink-100">
        <div
          className={cn("h-full transition-all", color)}
          style={{ width: `${Math.min(100, clamped)}%` }}
        />
        {over && (
          <div
            className="absolute top-0 h-full bg-fulkro-danger/60"
            style={{ left: "100%", width: `${clamped - 100}%` }}
          />
        )}
      </div>
      <span
        className={cn(
          "font-mono",
          // -700 shades for WCAG AA contrast.
          over ? "text-fulkro-danger-700" : "text-fulkro-ink-700",
        )}
      >
        {clamped}%
      </span>
    </div>
  );
}

export function RenewalClock({
  tMinusDays,
  expiresAt,
  className,
}: {
  tMinusDays: number;
  expiresAt?: string;
  className?: string;
}) {
  const rag: RagStatus =
    tMinusDays <= 60 ? "red" : tMinusDays <= 180 ? "amber" : "green";
  // -700 shade for WCAG AA contrast on /10 tinted bg (Phase A.1 rule).
  // Border /40 alpha kept (subtle visual indicator · text contrast is the
  // accessibility-critical concern).
  const style =
    rag === "red"
      ? "border-fulkro-danger/40 bg-fulkro-danger/10 text-fulkro-danger-700"
      : rag === "amber"
        ? "border-fulkro-warning/40 bg-fulkro-warning/10 text-fulkro-warning-700"
        : "border-fulkro-success/40 bg-fulkro-success/10 text-fulkro-success-700";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold",
        style,
        className,
      )}
      title={expiresAt ? `Vencimiento ${expiresAt}` : undefined}
    >
      T-{tMinusDays} d
    </span>
  );
}
