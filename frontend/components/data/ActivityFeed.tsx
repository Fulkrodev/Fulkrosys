import {
  FileCheck,
  FileText,
  ScanLine,
  Send,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import type { ActivityEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICON_BY_TYPE: Record<ActivityEvent["type"], LucideIcon> = {
  evidence_generated: FileText,
  scan_completed: ScanLine,
  proposal_sent: Send,
  document_signed: FileCheck,
  agent_run: Sparkles,
  other: FileText,
};

export function ActivityFeed({
  events,
  max,
  className,
  emptyLabel = "Aún no hay actividad registrada.",
}: {
  events: ActivityEvent[];
  max?: number;
  className?: string;
  emptyLabel?: string;
}) {
  const items = max ? events.slice(0, max) : events;

  if (items.length === 0) {
    return (
      <p className={cn("text-sm text-fulkro-ink-500", className)}>
        {emptyLabel}
      </p>
    );
  }

  return (
    <ul className={cn("space-y-3", className)}>
      {items.map((event) => {
        const Icon = ICON_BY_TYPE[event.type];
        return (
          <li key={event.id} className="flex items-start gap-3">
            <span className="mt-0.5 shrink-0 rounded-md bg-fulkro-ink-100 p-2 text-fulkro-primary-700">
              <Icon size={14} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-fulkro-ink-700">
                {event.description}
              </p>
              <p className="text-xs text-fulkro-ink-500">
                {relativeTime(event.timestamp)}
                {event.project_slug ? ` · ${event.project_slug}` : ""}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.max(0, Math.round((now - then) / 1000));
  if (diff < 60) return "hace unos segundos";
  if (diff < 3_600) return `hace ${Math.round(diff / 60)} min`;
  if (diff < 86_400) return `hace ${Math.round(diff / 3600)} h`;
  return `hace ${Math.round(diff / 86_400)} d`;
}
