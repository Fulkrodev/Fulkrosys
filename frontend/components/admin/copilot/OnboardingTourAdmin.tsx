"use client";

/**
 * OnboardingTourAdmin · primer admin login welcome modal.
 *
 * Sub-atom Sesión 3A Phase B.4 · variant analogous to cliente
 * OnboardingTutorial (existing MB-7 atom 7.3) but Marcos-focused with
 * 6 admin-specific steps (selector · roadmap · ProjectTabs · CopilotoDock ·
 * Pipeline comercial).
 *
 * localStorage flag `fulkro_admin_tour_completed` persists completion.
 * Skip-able · NO obligatorio.
 *
 * R30 admin tutor primer principios sostener.
 */
import { ChevronLeft, ChevronRight, Compass, X } from "lucide-react";
import { useEffect, useState } from "react";

const STORAGE_KEY = "fulkro_admin_tour_completed";

interface TourStep {
  title: string;
  body: string;
  /** Optional emoji icon for visual cue (NOT emoji in code · purely UX cosmetic). */
  pictogram?: string;
}

const STEPS: TourStep[] = [
  {
    title: "Bienvenido a FULKRO admin",
    body:
      "Te guiamos paso a paso para implantar el ENS RD 311/2022 a tus clientes. La plataforma combina motores deterministas (trazables ENAC) + copilotos LLM (asistencia conversacional) + workflow cronológico.",
    pictogram: "🚀",
  },
  {
    title: "Selecciona el proyecto al entrar",
    body:
      "Cada cliente tiene su propio proyecto · /admin/projects es tu home. Si solo tienes un proyecto, FULKRO te lleva directo al roadmap. Si tienes varios, eliges en el selector.",
    pictogram: "📁",
  },
  {
    title: "El roadmap es tu mapa",
    body:
      "/admin/projects/[id]/roadmap muestra las 10 fases ENS lifecycle · empieza por Categorización (M01) y avanza linear. Cada fase desbloquea la siguiente al firmar el hito.",
    pictogram: "🗺️",
  },
  {
    title: "Tabs del proyecto · todo a un click",
    body:
      "Cada proyecto tiene ~50 tabs organizados en MAIN_TABS (lifecycle ENS) + SUB_TABS (extras) + PROFILE_TABS (categoría/arquetipo). Tab AHORA pin-to-top siempre visible.",
    pictogram: "📑",
  },
  {
    title: "Copiloto siempre disponible",
    body:
      "Sidebar derecho con LLM Sonnet 4.6 · pregúntale sobre cualquier medida ENS o button-level UI · respuestas con citas Anexo II + RD 311/2022 + CCN-STIC. Atajo: tecla Ctrl+K (próximamente).",
    pictogram: "🤖",
  },
  {
    title: "Pipeline comercial",
    body:
      "/admin/pipeline para leads cualificados · da de alta el lead manualmente, genera la propuesta y avanza hacia la firma del contrato. Pre-piloto solo cliente directo: pipeline simple desde reunión.",
    pictogram: "📈",
  },
];

export function OnboardingTourAdmin() {
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
  if (!step) return null;
  const isLast = stepIdx === STEPS.length - 1;
  const isFirst = stepIdx === 0;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-label="Tour inicial admin FULKRO"
      data-testid="admin-tour-overlay"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-fulkro-primary-700">
            <Compass className="h-4 w-4" />
            Tour admin · Paso {stepIdx + 1} de {STEPS.length}
          </div>
          <button
            type="button"
            onClick={() => close(true)}
            aria-label="Saltar tour"
            className="grid h-7 w-7 place-items-center rounded-md text-fulkro-ink-500 hover:bg-fulkro-ink-100"
            data-testid="admin-tour-skip"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <h2 className="mt-3 flex items-center gap-2 text-xl font-bold text-fulkro-primary-700">
          {step.pictogram ? <span aria-hidden>{step.pictogram}</span> : null}
          {step.title}
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-fulkro-ink-700">
          {step.body}
        </p>

        <div className="mt-6 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => close(true)}
            className="text-sm font-medium text-fulkro-ink-500 hover:text-fulkro-ink-700"
          >
            Saltar
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isFirst}
              onClick={() => setStepIdx((s) => Math.max(0, s - 1))}
              className="inline-flex items-center gap-1 rounded-md border border-fulkro-ink-300 bg-fulkro-ink-100 px-3 py-1.5 text-sm font-bold text-fulkro-ink-700 disabled:opacity-40"
              data-testid="admin-tour-prev"
            >
              <ChevronLeft className="h-4 w-4" /> Atrás
            </button>
            {isLast ? (
              <button
                type="button"
                onClick={() => close(true)}
                className="rounded-md bg-fulkro-primary-700 px-4 py-1.5 text-sm font-bold text-white hover:bg-fulkro-primary-700/90"
                data-testid="admin-tour-finish"
              >
                Empezar
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStepIdx((s) => s + 1)}
                className="inline-flex items-center gap-1 rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-sm font-bold text-white hover:bg-fulkro-primary-700/90"
                data-testid="admin-tour-next"
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
