"use client";

import {
  AlertCircle,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  Calendar,
  CalendarClock,
  Clock,
  FileSearch,
  FileText,
  FileX,
  GitPullRequestArrow,
  Layers,
  ListChecks,
  Map as MapIcon,
  Server,
  ShieldAlert,
  TimerReset,
  Zap,
  type LucideIcon,
} from "lucide-react";
import * as React from "react";

import {
  fetchQuickActions,
  type QuickAction,
} from "@/lib/api/copilot-quick-actions";

const ICON_MAP: Record<string, LucideIcon> = {
  AlertCircle,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  Calendar,
  CalendarClock,
  Clock,
  FileSearch,
  FileText,
  FileX,
  GitPullRequestArrow,
  Layers,
  ListChecks,
  Map: MapIcon,
  Server,
  ShieldAlert,
  TimerReset,
  Zap,
};

export interface QuickActionButtonsProps {
  context?: string;
  projectId?: string;
  disabled?: boolean;
  onSelect: (prefillQuery: string) => void;
}

export function QuickActionButtons({
  context,
  projectId,
  disabled,
  onSelect,
}: QuickActionButtonsProps) {
  const [actions, setActions] = React.useState<QuickAction[]>([]);

  React.useEffect(() => {
    const controller = new AbortController();
    fetchQuickActions(context, projectId, controller.signal).then((items) => {
      if (!controller.signal.aborted) setActions(items);
    });
    return () => controller.abort();
  }, [context, projectId]);

  if (actions.length === 0) return null;

  return (
    <div
      role="list"
      aria-label="Acciones sugeridas del copiloto"
      className="scrollbar-fulkro-light -mx-1 flex gap-2 overflow-x-auto px-1 pb-1"
    >
      {actions.map((a) => {
        const Icon = ICON_MAP[a.icon] ?? Zap;
        return (
          <button
            key={a.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(a.prefill_query)}
            style={{
              backgroundColor: "var(--fulkro-surface-glass)",
              borderColor: "var(--fulkro-surface-glass-border)",
            }}
            className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold text-[color:var(--fulkro-title)] transition-colors hover:bg-[color:var(--fulkro-surface-glass-strong)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon className="h-3.5 w-3.5" strokeWidth={2.3} />
            {a.label}
          </button>
        );
      })}
    </div>
  );
}
