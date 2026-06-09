/**
 * ProjectCardWeekly · Zone 2 card normal · sub-atom 1.C.D.B.1 v3.8.
 *
 * Amarillo SUAVE (bg-amber-50 border-l-amber-500) · esta semana pendientes.
 */
"use client";

import Link from "next/link";
import { Calendar, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { CommandCenterProjectCard } from "@/lib/api/workflow-command-center";

export function ProjectCardWeekly({
  card,
}: {
  card: CommandCenterProjectCard;
}) {
  const detailHref = `/admin/workflow-command-center/projects/${card.project_id}`;
  return (
    <article
      className="border-l-4 border-l-amber-500 bg-amber-50 dark:bg-amber-950/30 rounded-r-lg p-3 shadow-sm"
      role="article"
      aria-label={`Esta semana · ${card.project_nombre}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Calendar className="size-3.5 text-amber-700 shrink-0" />
            <h4 className="font-medium text-sm truncate">{card.project_nombre}</h4>
            {card.categoria && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {card.categoria}
              </Badge>
            )}
          </div>
          {card.current_step_title && (
            <p className="text-xs text-foreground/70 line-clamp-1">
              {card.current_step_title}
            </p>
          )}
          <div className="text-[11px] text-foreground/55">
            {card.progress_completed}/{card.progress_total} ({card.progress_pct}%) ·
            urgencia {card.current_step_urgency}
          </div>
        </div>
        <Link
          href={detailHref}
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Revisar
          <ChevronRight className="ml-1 size-3" />
        </Link>
      </div>
    </article>
  );
}
