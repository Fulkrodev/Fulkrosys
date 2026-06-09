"use client";

/**
 * PhaseProgressWizard · stepper horizontal 10 fases lifecycle (MB-13.2 · ADR-035).
 *
 * Visualiza WorkflowPhase enum 10 fases canonical (ADR-026 + SAN-C MB-11.1) con
 * tres estados: completed (✓ verde) · current (ring primary) · future (lock muted).
 *
 * Click navega a tab fase para current/past · futuras bloqueadas (cursor + a11y).
 * Tooltip muestra nombre completo + descripción + estado.
 *
 * Reutiliza query `admin-dashboard` cache compartido con NextActionCard (TanStack
 * Query staleTime 15s + refetchInterval 30s) · SSE refines en MB-13.3.
 *
 * Coherencia visual: Tooltip shadcn + theme tokens fulkro-* + iconos lucide-react.
 */
import { useQuery } from "@tanstack/react-query";
import { Check, Lock } from "lucide-react";
import Link from "next/link";

import { getProjectDashboard } from "@/lib/admin-dashboard/api";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface PhaseDescriptor {
  /** WorkflowPhase enum value (snake_case) · key estable. */
  id: string;
  /** Etiqueta corta visible (≤8 chars typically). */
  short: string;
  /** Nombre completo legible ES (tooltip + screen-reader). */
  full: string;
  /** Descripción concreta lo que pasa en la fase (tooltip body). */
  description: string;
  /** URL relativa al proyecto (segmento sub-tab). Se concatena con projectId. */
  segment: string;
}

const PHASES: PhaseDescriptor[] = [
  {
    id: "pre_venta",
    short: "Pre-venta",
    full: "Pre-venta",
    description: "Reunión exploratoria · propuesta cualificada · contrato",
    segment: "summary",
  },
  {
    id: "onboarding",
    short: "Kick-off",
    full: "Kick-off / Onboarding",
    description: "Sesión cliente · roles · plan proyecto · acta inicial",
    segment: "roles",
  },
  {
    id: "diagnostico",
    short: "Diag.",
    full: "Diagnóstico",
    description: "M21 stakeholders · maturity scoring · informe diagnóstico",
    segment: "diagnosis",
  },
  {
    id: "analisis_riesgos",
    short: "Riesgos",
    full: "Análisis de riesgos",
    description: "MAGERIT · plan tratamiento · acta aceptación riesgo",
    segment: "risks",
  },
  {
    id: "adecuacion",
    short: "Adec.",
    full: "Plan de adecuación",
    description: "Categorización CCN-STIC 803 · gap CCN-STIC 808 · PdA 806",
    segment: "plan",
  },
  {
    id: "implantacion",
    short: "Implant.",
    full: "Implantación",
    description: "PSI + normativas + procedimientos + IT + evidencias",
    segment: "implementation",
  },
  {
    id: "dda_final",
    short: "DdA",
    full: "DdA final",
    description: "Declaración Aplicabilidad firmada RSEG · pre-verificación",
    segment: "documents",
  },
  {
    id: "verificacion",
    short: "Verif.",
    full: "Verificación",
    description: "M08 verification runs · pentest CPSTIC (Alta) · findings",
    segment: "verification",
  },
  {
    id: "conformidad",
    short: "Conf.",
    full: "Conformidad",
    description: "Auditoría CCN-STIC 802 · ENAC (M/A) · INES · distintivo",
    segment: "conformity",
  },
  {
    id: "retainer_cierre",
    short: "Retainer",
    full: "Retainer / Cierre",
    description: "Mejora continua · revisión anual · auditoría bienal",
    segment: "retainer",
  },
];

interface Props {
  projectId: string;
}

export function PhaseProgressWizard({ projectId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-dashboard", projectId],
    queryFn: () => getProjectDashboard(projectId),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <Skeleton className="mb-4 h-5 w-48" />
        <div className="flex gap-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-12 flex-1" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const currentIdx = data.phase_index;
  const totalPhases = PHASES.length;

  return (
    <TooltipProvider delayDuration={200}>
      <div
        className="rounded-lg border bg-card p-4"
        data-testid="phase-progress-wizard"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Progreso del proyecto</h3>
          <span className="text-xs text-muted-foreground">
            Fase {currentIdx + 1} de {totalPhases}
          </span>
        </div>

        <ol
          className="flex items-stretch gap-1 overflow-x-auto pb-2"
          aria-label="Fases lifecycle proyecto ENS"
        >
          {PHASES.map((phase, idx) => {
            const isCompleted = idx < currentIdx;
            const isCurrent = idx === currentIdx;
            const isFuture = idx > currentIdx;
            const url = `/admin/projects/${projectId}/${phase.segment}`;

            const stepInner = (
              <div className="flex w-full flex-col items-center gap-1 p-2">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors",
                    isCompleted && "bg-fulkro-success text-white",
                    isCurrent &&
                      "bg-fulkro-primary-700 text-white shadow-md ring-2 ring-fulkro-primary-300 ring-offset-2 ring-offset-background",
                    isFuture && "bg-muted text-muted-foreground",
                  )}
                  aria-hidden="true"
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : isFuture ? (
                    <Lock className="h-3 w-3" />
                  ) : (
                    idx + 1
                  )}
                </div>
                <span
                  className={cn(
                    "max-w-full truncate text-center text-xs",
                    isCurrent
                      ? "font-semibold text-foreground"
                      : "text-muted-foreground",
                  )}
                >
                  {phase.short}
                </span>
              </div>
            );

            return (
              <li
                key={phase.id}
                className="min-w-20 flex-1"
                aria-current={isCurrent ? "step" : undefined}
              >
                <Tooltip>
                  <TooltipTrigger asChild>
                    {isFuture ? (
                      <div
                        className="cursor-not-allowed rounded-md opacity-60"
                        aria-disabled="true"
                        aria-label={`${phase.full} (bloqueada)`}
                      >
                        {stepInner}
                      </div>
                    ) : (
                      <Link
                        href={url}
                        className="block rounded-md transition-colors hover:bg-muted/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700"
                        aria-label={`${phase.full}${
                          isCurrent ? " (fase actual)" : ""
                        }`}
                      >
                        {stepInner}
                      </Link>
                    )}
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <div className="space-y-1">
                      <p className="font-semibold">{phase.full}</p>
                      <p className="text-xs">{phase.description}</p>
                      {isFuture && (
                        <p className="text-xs italic text-muted-foreground">
                          Bloqueada · completar fases previas
                        </p>
                      )}
                      {isCurrent && (
                        <p className="text-xs italic">Fase actual</p>
                      )}
                    </div>
                  </TooltipContent>
                </Tooltip>
              </li>
            );
          })}
        </ol>

        <div
          className="mt-2 flex items-center gap-1 px-2"
          aria-hidden="true"
        >
          {PHASES.slice(0, -1).map((_, idx) => {
            const isDone = idx < currentIdx;
            return (
              <div
                key={idx}
                className={cn(
                  "h-0.5 flex-1 rounded-full",
                  isDone ? "bg-fulkro-success" : "bg-muted",
                )}
              />
            );
          })}
        </div>
      </div>
    </TooltipProvider>
  );
}
