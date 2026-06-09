/**
 * ProjectCardUrgent · Zone 1 hero card · sub-atom 1.C.D.B.1 v3.8.
 *
 * Rojo SUAVE (bg-red-50 border-l-red-500) · informativo NO alarma.
 * Per item: cliente + 1-line problema + ETA stuck + CTA primary inline.
 */
"use client";

import Link from "next/link";
import { AlertCircle, ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { CommandCenterProjectCard } from "@/lib/api/workflow-command-center";

export function ProjectCardUrgent({
  card,
}: {
  card: CommandCenterProjectCard;
}) {
  const detailHref = `/admin/workflow-command-center/projects/${card.project_id}`;
  return (
    <article
      className="border-l-4 border-l-red-500 bg-red-50 dark:bg-red-950/30 rounded-r-lg p-4 shadow-sm"
      role="article"
      aria-label={`Urgente · ${card.project_nombre}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <AlertCircle className="size-4 text-red-600 shrink-0" />
            <h3 className="font-semibold text-base truncate">
              {card.project_nombre}
            </h3>
            {card.categoria && (
              <Badge variant="outline" className="text-xs">
                {card.categoria}
              </Badge>
            )}
            {card.archetype && (
              <Badge variant="secondary" className="text-xs">
                {card.archetype}
              </Badge>
            )}
          </div>
          {card.current_step_title && (
            <p className="text-sm text-foreground/80 line-clamp-2">
              Step: <span className="font-medium">{card.current_step_title}</span>
            </p>
          )}
          <div className="flex items-center gap-3 text-xs text-foreground/70">
            <span>Fase: {card.current_phase}</span>
            <span>·</span>
            <span>
              Progreso: {card.progress_completed}/{card.progress_total} (
              {card.progress_pct}%)
            </span>
            <span>·</span>
            <span className="text-red-700 dark:text-red-400 font-semibold">
              Urgencia: {card.current_step_urgency}/100
            </span>
          </div>
        </div>
        <Link
          href={detailHref}
          className={cn(buttonVariants({ variant: "primary", size: "sm" }))}
        >
          Resolver ahora
          <ArrowRight className="ml-1 size-3" />
        </Link>
      </div>
    </article>
  );
}
