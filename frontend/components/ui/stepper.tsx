"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export interface StepperStep {
  id: string;
  label: string;
}

export interface StepperProps {
  steps: StepperStep[];
  currentIndex: number;
  className?: string;
}

/**
 * Stepper genérico (sub-fase 5.B FASE 5).
 *
 * Visual horizontal con indicador numérico → check tras pasar al
 * siguiente paso. Conectado por línea entre dots. Tailwind puro.
 *
 * Uso:
 *   <Stepper
 *     steps={[
 *       { id: "data", label: "Datos cliente" },
 *       { id: "user", label: "Primer usuario" },
 *       { id: "review", label: "Confirmación" },
 *     ]}
 *     currentIndex={0}
 *   />
 */
export function Stepper({ steps, currentIndex, className }: StepperProps) {
  return (
    <ol
      className={cn(
        "flex items-center gap-2 overflow-x-auto",
        className,
      )}
      aria-label="Wizard progreso"
    >
      {steps.map((step, i) => {
        const isComplete = i < currentIndex;
        const isCurrent = i === currentIndex;
        const isLast = i === steps.length - 1;

        return (
          <li
            key={step.id}
            className="flex flex-1 items-center gap-2"
            aria-current={isCurrent ? "step" : undefined}
          >
            <div className="flex flex-col items-center gap-1.5">
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                  isComplete && "bg-fulkro-success text-white",
                  isCurrent && "bg-fulkro-primary-700 text-white shadow-md",
                  !isComplete &&
                    !isCurrent &&
                    "bg-fulkro-ink-100 text-fulkro-ink-600",
                )}
                aria-label={step.label}
              >
                {isComplete ? <Check size={14} /> : i + 1}
              </span>
              <span
                className={cn(
                  "text-xs font-medium whitespace-nowrap",
                  isCurrent
                    ? "text-fulkro-primary-700"
                    : "text-fulkro-ink-500",
                )}
              >
                {step.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={cn(
                  "mt-[-18px] h-0.5 flex-1 transition-colors",
                  isComplete
                    ? "bg-fulkro-success"
                    : "bg-fulkro-ink-200",
                )}
                aria-hidden="true"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
