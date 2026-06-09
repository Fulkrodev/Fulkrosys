"use client";

/**
 * TodayActionsCards · zone 2 dashboard "Tu trabajo de hoy".
 *
 * Up to 5 actions priorizadas · celebratoria card if empty.
 */
import Link from "next/link";
import {
  AlertTriangle,
  BadgeCheck,
  ClipboardList,
  FileUp,
  ListChecks,
  PartyPopper,
  Repeat,
  Server,
  Shield,
  Sparkles,
  Upload,
  Users,
} from "lucide-react";

import type { AdaptiveAction } from "@/lib/api/dashboard";
import { priorityClasses } from "@/lib/adaptive-dashboard";

const ICONS: Record<string, typeof Sparkles> = {
  ClipboardList,
  Users,
  Server,
  ListChecks,
  Upload,
  Shield,
  BadgeCheck,
  Repeat,
  AlertTriangle,
  FileUp,
};

interface Props {
  actions: AdaptiveAction[];
}

export function TodayActionsCards({ actions }: Props) {
  if (!actions.length) {
    return (
      <section
        className="rounded-2xl border border-emerald-300/40 bg-emerald-500/10 px-6 py-8 text-center"
        data-testid="today-actions-empty"
      >
        <PartyPopper className="mx-auto h-10 w-10 text-emerald-600" />
        <h2 className="mt-3 text-xl font-bold text-emerald-700">
          ¡No tienes pendientes!
        </h2>
        <p className="mt-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
          Marcos te avisará cuando haya algo nuevo. Mientras tanto puedes
          revisar tu workflow.
        </p>
      </section>
    );
  }

  return (
    <section data-testid="today-actions" className="space-y-3">
      <h2 className="text-lg font-bold tracking-tight text-[color:var(--fulkro-title)]">
        Tu trabajo de hoy
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {actions.map((action) => {
          const Icon = ICONS[action.icon] ?? Sparkles;
          const prio = priorityClasses(action.priority);
          return (
            <article
              key={action.id}
              className="rounded-xl border border-fulkro-surface-glass-border bg-fulkro-surface-glass-strong px-5 py-4"
              data-testid={`action-card-${action.id}`}
            >
              <div className="flex items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-fulkro-surface-glass">
                  <Icon className="h-5 w-5 text-[color:var(--fulkro-subtitle)]" />
                </span>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-base font-bold leading-tight text-[color:var(--fulkro-title)]">
                      {action.title}
                    </h3>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${prio.bg} ${prio.fg}`}
                    >
                      {prio.label}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                    {action.description}
                  </p>
                  <div className="flex items-center justify-between pt-1 text-xs font-medium text-[color:var(--fulkro-muted)]">
                    <span>
                      ~{action.estimated_minutes} min
                      {action.requires_step_up && (
                        <span className="ml-2 rounded bg-amber-500/15 px-1.5 py-0.5 font-bold text-amber-700">
                          requiere OTP firma
                        </span>
                      )}
                    </span>
                    <Link
                      href={action.href}
                      className="rounded-md bg-[color:var(--fulkro-accent)] px-3 py-1.5 text-xs font-bold text-white hover:opacity-90"
                    >
                      Hacerlo ahora
                    </Link>
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
