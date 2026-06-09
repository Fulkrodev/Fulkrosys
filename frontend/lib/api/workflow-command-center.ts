/**
 * Frontend API · m_workflow_engine Admin Command Center (1.C.D.B v3.8).
 *
 * Consume 8 endpoints backend 1.C.D.A:
 *   - GET    /api/v1/admin/workflow-command-center (multi-cliente)
 *   - GET    /api/v1/admin/workflow-command-center/projects/{id} (per-cliente)
 *   - POST   /api/v1/admin/workflow-command-center/projects/{id}/steps/{template_id}/advance
 *   - GET    /api/v1/projects/{id}/workflow-engine/{catalog,current-step,progress,timeline}
 *
 * OPS-044 sostenido · usa `api()` wrapper con path completo (NO double prefix).
 */
import { api } from "@/lib/api";

// ============================================================
// Types · mirror Pydantic schemas backend m_workflow_engine
// ============================================================

export interface EnrichedStepState {
  template_id: string;
  phase: string;
  order_within_phase: number | null;
  title: string;
  description_detailed_es: string | null;
  rationale_es: string | null;
  cta_label: string | null;
  cta_url: string | null;
  priority: number;
  estimated_days: number | null;
  deliverable_codes: string[];
  prerequisite_template_ids: string[];
  actors: string[];
  completion_criteria_detailed: string[];
  adaptation_notes_es: string | null;
  tooltips_ens: Record<string, string>;
  is_enriched: boolean;
  variant_extra_focus: string | null;
  variant_reference_norms: string[];
  task_id: string | null;
  status: string; // not_started | pending | started | completed | blocked
  due_date_iso: string | null;
  started_at_iso: string | null;
  completed_at_iso: string | null;
  blocked_reason: string | null;
  urgency_score: number; // 0-100
  // 1.D.G v3.11 cross-actor state machine
  primary_actor?: "admin" | "cliente" | "system";
  dependency_status?: "blocked" | "available" | "in_progress" | "done";
  missing_prerequisites?: string[];
  estimated_days_to_complete?: number | null;
}

export interface CommandCenterProjectCard {
  project_id: string;
  project_nombre: string;
  categoria: string | null;
  archetype: string | null;
  current_phase: string;
  current_step_title: string | null;
  current_step_urgency: number;
  progress_pct: number;
  progress_completed: number;
  progress_total: number;
}

export interface CommandCenterResponse {
  urgentes_hoy: CommandCenterProjectCard[];
  esta_semana: CommandCenterProjectCard[];
  en_marcha: CommandCenterProjectCard[];
  proximos_30d: CommandCenterProjectCard[];
}

export interface ProjectDimsLike {
  categoria_objetivo: string | null;
  archetype: string | null;
  fase: string;
  tamano_empleados?: string;
  madurez_ens_actual?: string;
  procesa_datos_sensibles_rgpd9?: boolean;
  aplica_nis2?: string;
  aplica_dora?: string;
  aplica_ai_act?: string;
  dpo_designado?: string;
  arquitectura_sistemas?: string;
  multi_tenancy?: string;
  equipo_ti_tamano?: string;
  certificaciones_previas?: string[];
  urgencia_certificacion?: string;
  presupuesto_disponible?: string;
  compromiso_interno?: string;
  horas_cliente_semana?: string;
  [key: string]: unknown;
}

export interface ProjectCronologicaResponse {
  project_id: string;
  project_nombre: string;
  dims: ProjectDimsLike;
  current_phase: string;
  progress: {
    global_pct: number;
    global_completed: number;
    global_total: number;
    per_phase: Record<string, { completed: number; total: number; pct: number }>;
  };
  completed: EnrichedStepState[];
  ahora: EnrichedStepState | null;
  proximos_7d: EnrichedStepState[];
  proximos_30d: EnrichedStepState[];
}

export interface ProgressResponse {
  project_id: string;
  global_pct: number;
  global_completed: number;
  global_total: number;
  per_phase: Record<string, { completed: number; total: number; pct: number }>;
}

export interface CatalogResponse {
  project_id: string;
  dims: ProjectDimsLike;
  catalog: EnrichedStepState[];
  count: number;
}

export interface TimelineResponse {
  project_id: string;
  timeline: EnrichedStepState[];
  count: number;
}

export interface AdvanceStepResponse {
  task_id: string;
  template_id: string;
  status: string;
  completed_at: string | null;
}

// ============================================================
// ADMIN endpoints (multi-cliente · per-cliente)
// ============================================================

export async function getCommandCenterMultiClient(): Promise<CommandCenterResponse> {
  return api<CommandCenterResponse>("/api/v1/admin/workflow-command-center");
}

export async function getProjectCronologica(
  projectId: string,
): Promise<ProjectCronologicaResponse> {
  return api<ProjectCronologicaResponse>(
    `/api/v1/admin/workflow-command-center/projects/${projectId}`,
  );
}

export async function advanceStep(
  projectId: string,
  templateId: string,
): Promise<AdvanceStepResponse> {
  return api<AdvanceStepResponse>(
    `/api/v1/admin/workflow-command-center/projects/${projectId}/steps/${templateId}/advance`,
    { method: "POST" },
  );
}

// 1.D.G.D · Recordar al cliente

export interface RemindClientResponse {
  project_id: string;
  template_id: string;
  notified: boolean;
  channels: string[];
  message: string;
}

export async function remindClientStep(
  projectId: string,
  templateId: string,
): Promise<RemindClientResponse> {
  return api<RemindClientResponse>(
    `/api/v1/admin/workflow-command-center/projects/${projectId}/steps/${templateId}/remind`,
    { method: "POST" },
  );
}

// ============================================================
// INTERNOS endpoints (admin + cliente · ownership-checked)
// ============================================================

export async function getCatalog(
  projectId: string,
  phase?: string,
): Promise<CatalogResponse> {
  const url = new URL(
    `/api/v1/projects/${projectId}/workflow-engine/catalog`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost",
  );
  if (phase) url.searchParams.set("phase", phase);
  return api<CatalogResponse>(url.pathname + url.search);
}

export async function getCurrentStep(
  projectId: string,
): Promise<EnrichedStepState | null> {
  return api<EnrichedStepState | null>(
    `/api/v1/projects/${projectId}/workflow-engine/current-step`,
  );
}

export async function getProgress(projectId: string): Promise<ProgressResponse> {
  return api<ProgressResponse>(
    `/api/v1/projects/${projectId}/workflow-engine/progress`,
  );
}

export async function getTimeline(projectId: string): Promise<TimelineResponse> {
  return api<TimelineResponse>(
    `/api/v1/projects/${projectId}/workflow-engine/timeline`,
  );
}
