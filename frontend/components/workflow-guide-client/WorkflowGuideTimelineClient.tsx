"use client";

/**
 * WorkflowGuideTimelineClient · sub-atom 1.C.D.C.1 v3.8.
 *
 * Timeline vertical mono · 3 sections (vs 4 admin):
 *   ✅ COMPLETADO · compact summary celebratory (NO list completo)
 *   🎯 TU SIGUIENTE PASO · full expanded WorkflowStepCardClient
 *   📅 PRÓXIMOS PASOS · cards compact (NO "urgentes" · NO 30d forecast)
 *
 * R29 sostenido empíricamente:
 *   ✅ Empty states celebratorios encouraging
 *   ✅ Transitions friendly (NO "atrasado" · NO "te queda")
 *   ❌ NO contadores deadline coercitivos
 *   ❌ NO red flags · NO badges urgent
 */
import * as React from "react";
import { CheckCircle2, Sparkles, Target } from "lucide-react";

import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";

import { WorkflowStepCardClient } from "./WorkflowStepCardClient";
import { WorkflowStepCardCompact } from "./WorkflowStepCardCompact";

interface WorkflowGuideTimelineClientProps {
  completed: EnrichedStepState[];
  currentStep: EnrichedStepState | null;
  proximos: EnrichedStepState[];
  onOpenDetail?: (step: EnrichedStepState) => void;
  onMarkDone?: (step: EnrichedStepState) => void;
}

export function WorkflowGuideTimelineClient({
  completed,
  currentStep,
  proximos,
  onOpenDetail,
  onMarkDone,
}: WorkflowGuideTimelineClientProps) {
  const completedCount = completed.length;

  return (
    <div className="flex flex-col gap-6">
      {/* ─── COMPLETADO · compact summary ─── */}
      {completedCount > 0 ? (
        <section
          className="rounded-2xl border border-emerald-100 bg-emerald-50/50 px-5 py-4"
          aria-labelledby="completed-heading"
        >
          <div className="flex items-center gap-3">
            <CheckCircle2
              className="size-5 shrink-0 text-emerald-700"
              strokeWidth={2.3}
              aria-hidden
            />
            <div>
              <h2
                id="completed-heading"
                className="text-base font-semibold text-emerald-900"
              >
                Has completado {completedCount} {completedCount === 1 ? "paso" : "pasos"}
              </h2>
              <p className="text-sm text-emerald-700">
                ¡Buen trabajo! Sigue avanzando a tu ritmo.
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {/* ─── TU SIGUIENTE PASO · full expanded ─── */}
      <section aria-labelledby="next-step-heading">
        <h2
          id="next-step-heading"
          className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]"
        >
          <Target className="size-4 text-blue-600" strokeWidth={2.5} aria-hidden />
          Tu siguiente paso
        </h2>
        {currentStep ? (
          <WorkflowStepCardClient
            step={currentStep}
            onOpenDetail={onOpenDetail}
            onMarkDone={onMarkDone}
          />
        ) : (
          <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-6 text-center">
            <Sparkles
              className="mx-auto mb-3 size-8 text-emerald-500"
              strokeWidth={2.2}
              aria-hidden
            />
            <p className="text-base font-semibold text-emerald-900">
              ¡Lo estás haciendo genial! 🎉
            </p>
            <p className="mt-1 text-sm text-emerald-700">
              No hay pasos pendientes ahora mismo. Marcos revisará tu progreso.
            </p>
          </div>
        )}
      </section>

      {/* ─── PRÓXIMOS PASOS · compact cards ─── */}
      {proximos.length > 0 ? (
        <section aria-labelledby="upcoming-heading">
          <h2
            id="upcoming-heading"
            className="mb-3 text-sm font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]"
          >
            Próximos pasos
          </h2>
          <div className="flex flex-col gap-2.5">
            {proximos.map((step) => (
              <WorkflowStepCardCompact
                key={step.template_id}
                step={step}
                onOpenDetail={onOpenDetail}
              />
            ))}
          </div>
        </section>
      ) : currentStep ? (
        <section className="rounded-xl border border-blue-100 bg-blue-50/40 px-4 py-3">
          <p className="text-sm text-blue-900">
            Cuando termines el paso actual · te mostraré el siguiente.
          </p>
        </section>
      ) : null}
    </div>
  );
}
