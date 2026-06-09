"use client";

/**
 * OnboardingTutorial · MB-7 atom 7.3 plan v6.
 *
 * Simple guided tour · 5 steps · first-login auto-trigger · skip option.
 * localStorage flag 'fulkro_tutorial_completed' persists completion.
 *
 * Q5.4 plan v6 cement message: "Cualquier user de tu organización
 * puede operar y firmar" (NO role-based tooltips).
 */
import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";


const STORAGE_KEY = "fulkro_tutorial_completed";

interface TutorialStep {
  title: string;
  body: string;
}

const STEPS: TutorialStep[] = [
  {
    title: "Bienvenido a tu portal FULKRO",
    body:
      "Aquí gestionas tu proyecto ENS desde el diagnóstico hasta la certificación y el retainer post-cert.",
  },
  {
    title: "Tu workflow · 10 fases",
    body:
      "Tu dashboard te muestra siempre dónde estás y qué hay que hacer hoy. Las fases avanzan a medida que firmas hitos.",
  },
  {
    title: "Pulsa Copiloto cuando lo necesites",
    body:
      "El icono flotante abajo a la derecha abre el asistente FULKRO. Te responde con citas a la normativa ENS.",
  },
  {
    title: "Operación compartida",
    body:
      "Cualquier usuario de tu organización puede operar y firmar. Cada acción queda registrada con quién la hizo.",
  },
  {
    title: "Marcos te avisa",
    body:
      "Cuando hay algo pendiente o nuevo, recibes una notificación en la campana del header.",
  },
];


export function OnboardingTutorial() {
  const [isOpen, setIsOpen] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const done = window.localStorage.getItem(STORAGE_KEY);
      if (!done) setIsOpen(true);
    } catch {
      // localStorage unavailable · silently skip
    }
  }, []);

  const close = (markCompleted: boolean) => {
    if (markCompleted) {
      try {
        window.localStorage.setItem(STORAGE_KEY, "1");
      } catch {
        // ignore
      }
    }
    setIsOpen(false);
    setStepIdx(0);
  };

  if (!isOpen) return null;

  const step = STEPS[stepIdx];
  const isLast = stepIdx === STEPS.length - 1;
  const isFirst = stepIdx === 0;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-label="Tutorial inicial"
      data-testid="tutorial-overlay"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-accent)]">
            Paso {stepIdx + 1} de {STEPS.length}
          </div>
          <button
            type="button"
            onClick={() => close(true)}
            aria-label="Saltar tutorial"
            className="grid h-7 w-7 place-items-center rounded-md text-[color:var(--fulkro-muted)] hover:bg-fulkro-surface-glass-strong"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <h2 className="mt-3 text-xl font-bold text-[color:var(--fulkro-title)]">
          {step.title}
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-[color:var(--fulkro-body)]">
          {step.body}
        </p>

        <div className="mt-6 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => close(true)}
            className="text-sm font-medium text-[color:var(--fulkro-muted)] hover:text-[color:var(--fulkro-subtitle)]"
          >
            Saltar
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isFirst}
              onClick={() => setStepIdx((s) => Math.max(0, s - 1))}
              className="inline-flex items-center gap-1 rounded-md border border-fulkro-surface-glass-border bg-fulkro-surface-glass-strong px-3 py-1.5 text-sm font-bold text-[color:var(--fulkro-body)] disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" /> Atrás
            </button>
            {isLast ? (
              <button
                type="button"
                onClick={() => close(true)}
                className="rounded-md bg-[color:var(--fulkro-accent)] px-4 py-1.5 text-sm font-bold text-white hover:opacity-90"
                data-testid="tutorial-finish"
              >
                Empezar
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStepIdx((s) => s + 1)}
                className="inline-flex items-center gap-1 rounded-md bg-[color:var(--fulkro-accent)] px-3 py-1.5 text-sm font-bold text-white hover:opacity-90"
                data-testid="tutorial-next"
              >
                Siguiente <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
