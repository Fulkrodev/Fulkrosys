/**
 * ProjectRowCompact · Zone 3 compact row · sub-atom 1.C.D.B.1 v3.8.
 *
 * Verde SUAVE · 1-line per cliente · status verde · click navega.
 */
"use client";

import Link from "next/link";
import { CheckCircle2, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

import type { CommandCenterProjectCard } from "@/lib/api/workflow-command-center";

export function ProjectRowCompact({
  card,
}: {
  card: CommandCenterProjectCard;
}) {
  const detailHref = `/admin/workflow-command-center/projects/${card.project_id}`;
  return (
    <Link
      href={detailHref}
      className="flex items-center justify-between gap-3 rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-2 hover:bg-emerald-100 dark:hover:bg-emerald-950/50 transition-colors"
      role="link"
      aria-label={`En marcha · ${card.project_nombre}`}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <CheckCircle2 className="size-3.5 text-emerald-700 shrink-0" />
        <span className="font-medium text-sm truncate">{card.project_nombre}</span>
        {card.categoria && (
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0">
            {card.categoria}
          </Badge>
        )}
        <span className="text-xs text-foreground/70 truncate">
          fase {card.current_phase}
        </span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="hidden sm:block w-20">
          <Progress value={card.progress_pct} className="h-1.5" />
        </div>
        <span className="text-xs text-foreground/70 tabular-nums w-10 text-right">
          {card.progress_pct}%
        </span>
        <ChevronRight className="size-3.5 text-foreground/70" />
      </div>
    </Link>
  );
}
