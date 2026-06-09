/**
 * WorkflowTimelineAdmin · cronológica 4 sections vertical · refactor 1.D.F.0.C v3.11.
 *
 * Cambios 1.D.F.0.C:
 *   - AHORA sticky pin-to-top (CSS position: sticky · top-0 · z-10)
 *   - Otras secciones collapsible default (completado · próximos 7d · próximos 30d)
 *   - viewMode "ahora-only" oculta resto · "complete" muestra estructura 4 secciones
 *   - Sección AHORA empty state friendly cuando 0 tasks
 */
"use client";

import * as React from "react";
import { CheckCircle2, ChevronDown, ChevronRight, Clock } from "lucide-react";

import type {
  EnrichedStepState,
  ProjectDimsLike,
} from "@/lib/api/workflow-command-center";

import { WorkflowStepCardEnriched } from "./WorkflowStepCardEnriched";

export type WorkflowTimelineViewMode = "ahora-only" | "complete";

interface WorkflowTimelineAdminProps {
  projectId: string;
  dims: ProjectDimsLike;
  completed: EnrichedStepState[];
  ahora: EnrichedStepState | null;
  proximos7d: EnrichedStepState[];
  proximos30d: EnrichedStepState[];
  onOpenDetail?: (step: EnrichedStepState) => void;
  viewMode?: WorkflowTimelineViewMode;
}

export function WorkflowTimelineAdmin({
  projectId,
  dims,
  completed,
  ahora,
  proximos7d,
  proximos30d,
  onOpenDetail,
  viewMode = "complete",
}: WorkflowTimelineAdminProps) {
  // En vista completa los tabs históricos arrancan colapsados (Marcos foco AHORA)
  const [completedExpanded, setCompletedExpanded] = React.useState(false);
  const [proximos7dExpanded, setProximos7dExpanded] = React.useState(false);
  const [proximos30dExpanded, setProximos30dExpanded] = React.useState(false);

  const isAhoraOnly = viewMode === "ahora-only";

  return (
    <div className="space-y-6" data-testid="workflow-timeline-admin">
      {/* AHORA · sticky pin-to-top SIEMPRE visible · z-10 sobre cards */}
      <section
        aria-labelledby="ahora-heading"
        className="sticky top-0 z-10 bg-background pb-2 pt-1 -mx-1 px-1 rounded"
        data-testid="ahora-section"
      >
        <h3
          id="ahora-heading"
          className="text-sm font-semibold uppercase tracking-wide text-primary mb-3 flex items-center gap-2"
        >
          <Clock className="size-4 animate-pulse" />
          ━━━ AHORA
        </h3>
        {ahora ? (
          <WorkflowStepCardEnriched
            step={ahora}
            dims={dims}
            projectId={projectId}
            variant="ahora"
            onOpenDetail={onOpenDetail}
          />
        ) : (
          <p
            className="text-sm italic text-foreground/70 ml-6"
            data-testid="ahora-empty-state"
          >
            ✨ Todo al día. Sin sub-pasos urgentes ahora mismo.
          </p>
        )}
      </section>

      {/* Cuando "ahora-only" ocultamos completado + próximos */}
      {!isAhoraOnly && (
        <>
          {/* COMPLETADO · collapsible · default colapsado */}
          {completed.length > 0 && (
            <section
              aria-labelledby="completed-heading"
              data-testid="completed-section"
            >
              <button
                type="button"
                onClick={() => setCompletedExpanded((x) => !x)}
                className="flex items-center gap-2 w-full text-left mb-3 group"
                data-testid="completed-toggle"
              >
                <CheckCircle2 className="size-4 text-emerald-700" />
                <h3
                  id="completed-heading"
                  className="text-sm font-semibold uppercase tracking-wide text-foreground/70"
                >
                  ━━━ COMPLETADO ({completed.length})
                </h3>
                {completedExpanded ? (
                  <ChevronDown className="size-3.5 text-foreground/70" />
                ) : (
                  <ChevronRight className="size-3.5 text-foreground/70" />
                )}
              </button>
              {completedExpanded ? (
                <div className="space-y-2">
                  {completed.map((s) => (
                    <WorkflowStepCardEnriched
                      key={s.template_id}
                      step={s}
                      dims={dims}
                      projectId={projectId}
                      variant="compact"
                      onOpenDetail={onOpenDetail}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-foreground/70 italic ml-6">
                  {completed.length} sub-paso{completed.length === 1 ? "" : "s"}{" "}
                  completado{completed.length === 1 ? "" : "s"} · click para
                  expandir
                </p>
              )}
            </section>
          )}

          {/* PRÓXIMOS 7d · collapsible · default colapsado */}
          {proximos7d.length > 0 && (
            <section
              aria-labelledby="proximos7d-heading"
              data-testid="proximos7d-section"
            >
              <button
                type="button"
                onClick={() => setProximos7dExpanded((x) => !x)}
                className="flex items-center gap-2 w-full text-left mb-3 group"
                data-testid="proximos7d-toggle"
              >
                <h3
                  id="proximos7d-heading"
                  className="text-sm font-semibold uppercase tracking-wide text-foreground/70"
                >
                  ━━━ PRÓXIMOS 7 DÍAS ({proximos7d.length})
                </h3>
                {proximos7dExpanded ? (
                  <ChevronDown className="size-3.5 text-foreground/70" />
                ) : (
                  <ChevronRight className="size-3.5 text-foreground/70" />
                )}
              </button>
              {proximos7dExpanded ? (
                <div className="space-y-2">
                  {proximos7d.map((s) => (
                    <WorkflowStepCardEnriched
                      key={s.template_id}
                      step={s}
                      dims={dims}
                      projectId={projectId}
                      variant="compact"
                      onOpenDetail={onOpenDetail}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-foreground/70 italic ml-6">
                  {proximos7d.length} tarea{proximos7d.length === 1 ? "" : "s"} ·
                  click para expandir
                </p>
              )}
            </section>
          )}

          {/* PRÓXIMOS 30d · collapsible · default colapsado */}
          {proximos30d.length > 0 && (
            <section
              aria-labelledby="proximos30d-heading"
              data-testid="proximos30d-section"
            >
              <button
                type="button"
                onClick={() => setProximos30dExpanded((x) => !x)}
                className="flex items-center gap-2 w-full text-left mb-3 group"
                data-testid="proximos30d-toggle"
              >
                <h3
                  id="proximos30d-heading"
                  className="text-sm font-semibold uppercase tracking-wide text-foreground/70"
                >
                  ━━━ PRÓXIMOS 30 DÍAS ({proximos30d.length})
                </h3>
                {proximos30dExpanded ? (
                  <ChevronDown className="size-3.5 text-foreground/70" />
                ) : (
                  <ChevronRight className="size-3.5 text-foreground/70" />
                )}
              </button>
              {proximos30dExpanded ? (
                <div className="space-y-2">
                  {proximos30d.map((s) => (
                    <WorkflowStepCardEnriched
                      key={s.template_id}
                      step={s}
                      dims={dims}
                      projectId={projectId}
                      variant="compact"
                      onOpenDetail={onOpenDetail}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-foreground/70 italic ml-6">
                  {proximos30d.length} tarea{proximos30d.length === 1 ? "" : "s"}{" "}
                  · click para expandir
                </p>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
