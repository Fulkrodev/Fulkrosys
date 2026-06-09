"use client";

/**
 * HeroAdaptativo · zone 1 dashboard MB-7 atom 7.1.
 *
 * Greeting + tier badge + phase stepper + days countdown + archetype hint.
 * 4-dim context only (NO role).
 */
import type { DashboardContext, WorkflowSummary } from "@/lib/api/dashboard";
import { phaseLabel, tierConfig } from "@/lib/adaptive-dashboard";

interface Props {
  context: DashboardContext;
  workflowSummary: WorkflowSummary;
}

export function HeroAdaptativo({ context, workflowSummary }: Props) {
  const tier = tierConfig(context.categoria_objetivo);
  const greeting = context.client_name
    ? `Hola ${context.client_name}`
    : "Hola";

  return (
    <section
      className="rounded-2xl border border-fulkro-surface-glass-border bg-fulkro-surface-glass px-6 py-6 md:px-10 md:py-8"
      data-testid="hero-adaptativo"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-3">
          <h1 className="text-2xl font-bold tracking-tight text-[color:var(--fulkro-title)] md:text-3xl">
            {greeting}
          </h1>
          {context.project_name && (
            <p className="text-base font-medium text-[color:var(--fulkro-subtitle)]">
              Proyecto: <span className="font-bold">{context.project_name}</span>
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 pt-1">
            {context.categoria_objetivo && (
              <span
                className={`inline-flex items-center rounded-full px-4 py-1.5 text-sm font-bold ring-1 ${tier.bg} ${tier.fg}`}
              >
                Categoría {tier.label}
              </span>
            )}
            {context.current_phase && (
              <span className="inline-flex items-center rounded-full bg-fulkro-surface-glass-strong px-4 py-1.5 text-sm font-semibold text-[color:var(--fulkro-body)] ring-1 ring-fulkro-surface-glass-border">
                {phaseLabel(context.current_phase)}
                {context.phase_step != null && (
                  <span className="ml-2 text-[color:var(--fulkro-muted)]">
                    · paso {context.phase_step} de {context.phase_total}
                  </span>
                )}
              </span>
            )}
          </div>
          {workflowSummary.archetype_hint && (
            <p className="mt-2 max-w-2xl text-sm font-medium italic text-[color:var(--fulkro-muted)]">
              {workflowSummary.archetype_hint}
            </p>
          )}
        </div>

        {context.days_to_certification != null && (
          <div className="rounded-xl bg-fulkro-surface-glass-strong px-5 py-4 text-center ring-1 ring-fulkro-surface-glass-border md:min-w-[200px]">
            <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Hasta certificación
            </p>
            <p className="mt-1 text-4xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
              {context.days_to_certification}
            </p>
            <p className="text-xs font-medium text-[color:var(--fulkro-muted)]">
              días restantes
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
