/**
 * Adaptive dashboard helpers · MB-7 atom 7.1 plan v6.
 *
 * Lookup tables for tier badges, phase labels, archetype hints.
 * Visual constants ONLY — backend remains source of truth for data.
 */
import type { WorkflowPhase } from "@/lib/api/dashboard";

export const TIER_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  BASICA: {
    bg: "bg-emerald-500/15 ring-emerald-500/40",
    fg: "text-emerald-700",
    label: "BÁSICA",
  },
  MEDIA: {
    bg: "bg-sky-500/15 ring-sky-500/40",
    fg: "text-sky-700",
    label: "MEDIA",
  },
  ALTA: {
    bg: "bg-violet-500/15 ring-violet-500/40",
    fg: "text-violet-700",
    label: "ALTA",
  },
};

// Etiquetas amigables (R29) alineadas al enum canónico de 10 fases del
// backend (WorkflowPhase.ordered() · projects.fase). El orden y las claves
// DEBEN coincidir con backend/app/core/workflow_phase.py para que el
// stepper resalte la fase actual emitida por el dashboard.
export const PHASE_LABELS: Record<string, string> = {
  pre_venta: "Preparación inicial",
  onboarding: "Onboarding",
  diagnostico: "Diagnóstico",
  analisis_riesgos: "Análisis de riesgos",
  adecuacion: "Adecuación",
  implantacion: "Implantación",
  dda_final: "Declaración de Aplicabilidad",
  verificacion: "Verificación técnica",
  conformidad: "Conformidad ENS",
  retainer_cierre: "Cierre · oferta retainer",
};

export const PHASE_ORDER: WorkflowPhase[] = [
  "pre_venta",
  "onboarding",
  "diagnostico",
  "analisis_riesgos",
  "adecuacion",
  "implantacion",
  "dda_final",
  "verificacion",
  "conformidad",
  "retainer_cierre",
];

export function phaseLabel(phase: string | null | undefined): string {
  if (!phase) return "—";
  return PHASE_LABELS[phase] ?? phase;
}

export function tierConfig(categoria: string | null | undefined): {
  bg: string;
  fg: string;
  label: string;
} {
  return (
    TIER_COLORS[categoria ?? ""] ?? {
      bg: "bg-slate-500/15 ring-slate-500/40",
      fg: "text-slate-700",
      label: "—",
    }
  );
}

export function priorityClasses(priority: "high" | "medium" | "low"): {
  bg: string;
  fg: string;
  label: string;
} {
  if (priority === "high") {
    return { bg: "bg-rose-500/15", fg: "text-rose-700", label: "Alta" };
  }
  if (priority === "medium") {
    return { bg: "bg-amber-500/15", fg: "text-amber-700", label: "Media" };
  }
  return { bg: "bg-slate-500/15", fg: "text-slate-700", label: "Baja" };
}
