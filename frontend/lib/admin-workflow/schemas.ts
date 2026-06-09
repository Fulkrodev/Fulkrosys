/**
 * Admin Workflow schemas TypeScript (sub-bloque 8.B.2 FASE 8 · ADR-026
 * + SAN-C MB-11.1 extensión 10 fases canonical).
 *
 * Espejo de backend/app/core/workflow_schemas.py + workflow_phase.py.
 * Mantener sincronizado manualmente al cambiar contratos backend.
 *
 * 10 fases lifecycle canonical (Manual ENS plan v4.2):
 *   - analisis_riesgos sub-fase de diagnostico (Manual fase 4)
 *   - dda_final sub-fase de implantacion (Manual fase 7)
 */

export const WORKFLOW_PHASES = [
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
] as const;

export type WorkflowPhase = (typeof WORKFLOW_PHASES)[number];

export const PHASE_LABELS: Record<WorkflowPhase, string> = {
  pre_venta: "Pre-venta",
  onboarding: "Onboarding",
  diagnostico: "Diagnóstico",
  analisis_riesgos: "Análisis de riesgos",
  adecuacion: "Adecuación",
  implantacion: "Implantación",
  dda_final: "DdA final",
  verificacion: "Verificación",
  conformidad: "Conformidad",
  retainer_cierre: "Retainer / Cierre",
};

export type PhaseStatus = "pending" | "in_progress" | "done";
export type TaskStatus = "pending" | "in_progress" | "completed";
export type TaskPriority = "high" | "medium" | "low";

export interface NextAction {
  action_id: string;
  label: string;
  motor: string;
  endpoint: string | null;
  priority: number;
  estimated_minutes: number;
}

export interface PhaseProgress {
  phase: WorkflowPhase;
  pct_completed: number;
  total_items: number;
  items_done: number;
  status: PhaseStatus;
}

export interface TaskItem {
  label: string;
  motor: string;
  priority: TaskPriority;
  ord: number;
  status: TaskStatus;
}

export interface PhaseRoadmapEntry {
  phase: WorkflowPhase;
  status: PhaseStatus;
  pct_completed: number;
  is_current: boolean;
}

export interface WorkflowRoadmap {
  project_id: string;
  current_phase: WorkflowPhase;
  phases: PhaseRoadmapEntry[];
}
