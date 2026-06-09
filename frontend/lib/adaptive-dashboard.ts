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

export const PHASE_LABELS: Record<string, string> = {
  onboarding: "Onboarding",
  diagnostico: "Diagnóstico",
  magerit: "Análisis MAGERIT",
  dda: "Declaración de Aplicabilidad",
  implantacion: "Implantación",
  verificacion: "Verificación técnica",
  auditoria: "Auditoría",
  conformidad: "Conformidad ENS",
  retainer_cierre: "Cierre · oferta retainer",
  retainer_activo: "Retainer activo",
};

export const PHASE_ORDER: WorkflowPhase[] = [
  "onboarding",
  "diagnostico",
  "magerit",
  "dda",
  "implantacion",
  "verificacion",
  "auditoria",
  "conformidad",
  "retainer_cierre",
  "retainer_activo",
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
