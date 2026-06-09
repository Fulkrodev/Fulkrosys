"use client";

/**
 * WorkflowProgressBarClient · sub-atom 1.C.D.C.1 v3.8.
 *
 * Barra progreso celebratory · mensajes encouraging.
 *
 * R29 sostenido (audit pre-commit empírico):
 *   ✅ "¡Vas genial! 💪" si > 50%
 *   ✅ "Has completado X pasos · sigue así" si entre 20-50%
 *   ✅ "Estás empezando · cada paso cuenta" si < 20%
 *   ❌ NO "te falta..." · NO "queda..." · NO countdown coercitivo
 *   ❌ NO red colors urgentes · NO blinking · NO alarming
 */
import * as React from "react";
import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

interface WorkflowProgressBarClientProps {
  pct: number;
  completed: number;
  total: number;
  className?: string;
}

function encouragingMessage(pct: number, completed: number): string {
  if (pct >= 90) return "¡Casi al final! Lo estás haciendo genial 🎉";
  if (pct >= 75) return "¡Vas estupendamente! 💪";
  if (pct >= 50) return "¡Vas genial! 💪";
  if (pct >= 20) {
    return `Has completado ${completed} ${completed === 1 ? "paso" : "pasos"} · sigue así`;
  }
  if (completed > 0) {
    return `Has completado ${completed} ${completed === 1 ? "paso" : "pasos"} · cada paso cuenta`;
  }
  return "Estás empezando · cada paso cuenta";
}

export function WorkflowProgressBarClient({
  pct,
  completed,
  total,
  className,
}: WorkflowProgressBarClientProps) {
  const safePct = Math.max(0, Math.min(100, pct));
  const message = encouragingMessage(safePct, completed);

  return (
    <div
      className={cn(
        "rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-5",
        className,
      )}
      aria-label="Progreso del proyecto"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-blue-500" strokeWidth={2.2} />
          <h2 className="text-base font-bold text-[color:var(--fulkro-title)]">
            Tu progreso
          </h2>
        </div>
        <span className="text-sm font-semibold text-blue-700">
          {completed} / {total} pasos
        </span>
      </div>

      <div
        className="relative h-3 w-full overflow-hidden rounded-full bg-blue-100/70"
        role="progressbar"
        aria-valuenow={safePct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-700"
          style={{ width: `${safePct}%` }}
        />
      </div>

      <p className="mt-3 text-sm font-medium text-blue-900">{message}</p>
    </div>
  );
}
