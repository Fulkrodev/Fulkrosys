/**
 * ForecastTimeline30d · Zone 4 timeline horizontal · sub-atom 1.C.D.B.1 v3.8.
 *
 * Forecast hitos próximos 30 días · stepper horizontal compact.
 * Anticipa carga · no surprise.
 */
"use client";

import Link from "next/link";
import { Calendar, Clock } from "lucide-react";

import type { CommandCenterProjectCard } from "@/lib/api/workflow-command-center";

export function ForecastTimeline30d({
  cards,
}: {
  cards: CommandCenterProjectCard[];
}) {
  if (cards.length === 0) {
    return (
      <div className="text-sm text-foreground/55 italic">
        Sin hitos planificados próximos 30 días
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <ol className="space-y-2">
        {cards.slice(0, 8).map((card) => {
          const detailHref = `/admin/workflow-command-center/projects/${card.project_id}`;
          return (
            <li key={card.project_id}>
              <Link
                href={detailHref}
                className="flex items-center gap-3 rounded-md border border-border/50 px-3 py-2 hover:bg-muted/50 transition-colors"
              >
                <div className="flex size-7 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 shrink-0">
                  <Calendar className="size-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {card.project_nombre}
                  </p>
                  <p className="text-xs text-foreground/60 truncate">
                    {card.current_step_title ?? `Fase ${card.current_phase}`}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs text-foreground/55 shrink-0">
                  <Clock className="size-3" />
                  <span>{card.progress_pct}%</span>
                </div>
              </Link>
            </li>
          );
        })}
      </ol>
      {cards.length > 8 && (
        <p className="text-xs text-foreground/55 italic">
          + {cards.length - 8} hitos más en próximos 30 días
        </p>
      )}
    </div>
  );
}
