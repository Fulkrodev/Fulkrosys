/**
 * Motor 4 (Gap Analysis) + Motor 5 (Obligations) API client (zero-mock).
 *
 * 19 endpoints reales bajo /api/v1 (router prefix), agrupados:
 *  - M04 Gap Analysis: 9 endpoints (/projects/{id}/gaps/*, /gaps/{id}/*)
 *  - M05 Obligations:  10 endpoints (/projects/{id}/obligations/*, instantiate, gantt)
 *
 * Tipos espejo de los Pydantic schemas en
 *  backend/app/motors/m04_gap/schemas.py
 *  backend/app/motors/m05_obligations/api.py (inline schemas + types.py)
 *
 * Usa api() wrapper con CSRF + credentials.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

// ===================================================================
// Tipos M04 - Gap Analysis (espejo schemas.py)
// ===================================================================

export type GapSeveridad = "critica" | "alta" | "media" | "baja" | string;
export type GapEstado = "abierto" | "en_curso" | "cerrado" | string;
export type GapSemaforo = "rojo" | "amarillo" | "verde";

export interface GapFindingOut {
  id: string;
  project_id: string;
  fuente: string | null;
  severidad: GapSeveridad | null;
  medida_afectada: string | null;
  descripcion: string | null;
  evidencia_relacionada: string | null;
  estado: GapEstado | null;
  asignado_a: string | null;
  fecha_objetivo: string | null;
  metadata_jsonb: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
}

export interface GapFindingUpdate {
  severidad?: string | null;
  estado?: string | null;
  asignado_a?: string | null;
  fecha_objetivo?: string | null;
  descripcion?: string | null;
}

export interface CloseGapRequest {
  resolution_notes: string;
  closed_by?: string | null;
}

export interface AnalyzeProjectRequest {
  force?: boolean;
  categoria_objetivo?: string | null;
}

export interface AnalyzeProjectResponse {
  project_id: string;
  categoria_usada: string;
  dda_entries_evaluated: number;
  gaps_created: number;
  gaps_by_severidad: Record<string, number>;
  quick_wins_count: number;
  critical_nuclear_gaps: string[];
  catalog_version: string;
  generated_at: string;
}

export interface GapDashboardItem {
  id: string;
  medida_afectada: string | null;
  severidad: string | null;
  severidad_numeric: number;
  estado: string | null;
  esfuerzo_horas: number | null;
  quick_win: boolean;
  nuclear: boolean;
  familia: string | null;
  semaforo: GapSemaforo | string;
}

export interface GapDashboardResponse {
  project_id: string;
  total_gaps: number;
  by_severidad: Record<string, number>;
  by_familia: Record<string, number>;
  by_estado: Record<string, number>;
  by_semaforo: Record<string, number>;
  top_10_critical: GapDashboardItem[];
  quick_wins: GapDashboardItem[];
  nuclear_gaps: GapDashboardItem[];
  generated_at: string;
}

export interface GapListFilters {
  severidad?: string;
  estado?: string;
  familia?: string;
  only_quick_wins?: boolean;
  only_nuclear?: boolean;
}

export interface PrioritizeGapsLLMBody {
  client_context: {
    sector: "sanidad" | "aapp" | "fintech" | "otro" | string;
    ens_category: "BASICA" | "MEDIA" | "ALTA" | string;
    size?: "PYME" | "mediana" | "grande" | string;
  };
  only_open?: boolean;
  max_gaps?: number;
}

export interface PrioritizeGapsLLMResponse {
  project_id: string;
  input_gaps_count: number;
  prioritized?: unknown[];
  summary?: unknown;
  [key: string]: unknown;
}

// ===================================================================
// Tipos M05 - Obligations (espejo api.py inline + Obligation model)
// ===================================================================

export type ObligationEstado =
  | "pendiente"
  | "en_curso"
  | "completada"
  | "verificada"
  | "bloqueada"
  | string;

export interface ObligationOut {
  id: string;
  project_id: string;
  gap_id: string | null;
  titulo: string;
  descripcion: string;
  measure_code: string | null;
  tipo_ejecucion: string | null;
  modo_ejecucion: string | null;
  estado: ObligationEstado;
  responsable: string | null;
  esfuerzo_estimado: number | null;
  fecha_objetivo: string | null;
  fecha_completado: string | null;
  entregable_esperado: string | null;
  template_id: string | null;
  created_at: string | null;
  magic_link?: {
    magic_link_id: string;
    url: string;
    expires_at: string;
  };
}

export interface ListObligationsResponse {
  obligations: ObligationOut[];
}

export interface ObligationsListFilters {
  estado?: string;
  modo?: string;
  measure?: string;
}

export interface ObligationsSummary {
  total: number;
  by_estado: Record<string, number>;
  pendientes: number;
  en_curso: number;
  completadas: number;
  verificadas: number;
}

export interface CreateObligationBody {
  titulo: string;
  descripcion: string;
  measure_code?: string | null;
  tipo_ejecucion?: string | null;
  modo_ejecucion?: string | null;
  responsable?: string | null;
  esfuerzo_estimado?: number | null;
  fecha_objetivo?: string | null;
  gap_id?: string | null;
  entregable_esperado?: string | null;
}

export interface UpdateObligationBody {
  titulo?: string | null;
  descripcion?: string | null;
  responsable?: string | null;
  modo_ejecucion?: string | null;
  estado?: ObligationEstado | null;
  esfuerzo_estimado?: number | null;
  fecha_objetivo?: string | null;
}

export interface InstantiateGapItem {
  gap_id: string;
  measure_code: string;
}

export interface InstantiateRequest {
  nombre_proyecto: string;
  categoria_ens: string;
  cliente: { razon_social: string; sector?: string | null };
  gaps: InstantiateGapItem[];
  use_llm_personalization?: boolean;
}

export interface InstantiateOutcomeItem {
  gap_id: string | null;
  measure_code: string;
  created: number;
  existing: number;
  validation_errors: string[];
}

export interface InstantiateResponse {
  total_created: number;
  total_existing: number;
  outcomes: InstantiateOutcomeItem[];
}

export interface GanttRequestParams {
  fecha_kickoff: string;
  dedicacion_horas_semana?: number;
  format?: "json" | "xlsx";
}

// ===================================================================
// M04 - Gap Analysis API functions
// ===================================================================

export function analyzeProjectGaps(
  projectId: string,
  body: AnalyzeProjectRequest = {},
): Promise<AnalyzeProjectResponse> {
  return api<AnalyzeProjectResponse>(
    `${BASE}/projects/${projectId}/gaps/analyze`,
    { method: "POST", json: body },
  );
}

export function getGap(gapId: string): Promise<GapFindingOut> {
  return api<GapFindingOut>(`${BASE}/gaps/${gapId}`);
}

export function listGaps(
  projectId: string,
  filters: GapListFilters = {},
): Promise<GapFindingOut[]> {
  const qs = new URLSearchParams();
  if (filters.severidad) qs.set("severidad", filters.severidad);
  if (filters.estado) qs.set("estado", filters.estado);
  if (filters.familia) qs.set("familia", filters.familia);
  if (filters.only_quick_wins) qs.set("only_quick_wins", "true");
  if (filters.only_nuclear) qs.set("only_nuclear", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<GapFindingOut[]>(
    `${BASE}/projects/${projectId}/gaps${suffix}`,
  );
}

export function updateGap(
  gapId: string,
  body: GapFindingUpdate,
): Promise<GapFindingOut> {
  return api<GapFindingOut>(`${BASE}/gaps/${gapId}`, {
    method: "PATCH",
    json: body,
  });
}

export function deleteGap(gapId: string): Promise<void> {
  return api<void>(`${BASE}/gaps/${gapId}`, { method: "DELETE" });
}

export function closeGap(
  gapId: string,
  body: CloseGapRequest,
): Promise<GapFindingOut> {
  return api<GapFindingOut>(`${BASE}/gaps/${gapId}/close`, {
    method: "POST",
    json: body,
  });
}

export function getGapDashboard(
  projectId: string,
): Promise<GapDashboardResponse> {
  return api<GapDashboardResponse>(
    `${BASE}/projects/${projectId}/gaps/dashboard`,
  );
}

export function getGapQuickWins(
  projectId: string,
): Promise<GapDashboardItem[]> {
  return api<GapDashboardItem[]>(
    `${BASE}/projects/${projectId}/gaps/quick-wins`,
  );
}

export function prioritizeGapsLLM(
  projectId: string,
  body: PrioritizeGapsLLMBody,
): Promise<PrioritizeGapsLLMResponse> {
  return api<PrioritizeGapsLLMResponse>(
    `${BASE}/projects/${projectId}/gaps/prioritize-llm`,
    { method: "POST", json: body },
  );
}

// ===================================================================
// M05 - Obligations API functions
// ===================================================================

export function instantiateObligations(
  projectId: string,
  body: InstantiateRequest,
): Promise<InstantiateResponse> {
  return api<InstantiateResponse>(
    `${BASE}/projects/${projectId}/obligations/instantiate`,
    { method: "POST", json: body },
  );
}

export function getObligationsGanttUrl(
  projectId: string,
  params: GanttRequestParams,
): string {
  const qs = new URLSearchParams();
  qs.set("fecha_kickoff", params.fecha_kickoff);
  if (params.dedicacion_horas_semana !== undefined) {
    qs.set("dedicacion_horas_semana", String(params.dedicacion_horas_semana));
  }
  if (params.format) qs.set("format", params.format);
  return `${BASE}/projects/${projectId}/obligations/gantt?${qs.toString()}`;
}

export function getObligationsGantt(
  projectId: string,
  params: GanttRequestParams,
): Promise<unknown> {
  return api<unknown>(getObligationsGanttUrl(projectId, params));
}

export function createObligation(
  projectId: string,
  body: CreateObligationBody,
): Promise<ObligationOut> {
  return api<ObligationOut>(
    `${BASE}/projects/${projectId}/obligations`,
    { method: "POST", json: body },
  );
}

export function listObligations(
  projectId: string,
  filters: ObligationsListFilters = {},
): Promise<ListObligationsResponse> {
  const qs = new URLSearchParams();
  if (filters.estado) qs.set("estado", filters.estado);
  if (filters.modo) qs.set("modo", filters.modo);
  if (filters.measure) qs.set("measure", filters.measure);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<ListObligationsResponse>(
    `${BASE}/projects/${projectId}/obligations${suffix}`,
  );
}

export function getObligationsSummary(
  projectId: string,
): Promise<ObligationsSummary> {
  return api<ObligationsSummary>(
    `${BASE}/projects/${projectId}/obligations/summary`,
  );
}

export function getObligation(
  projectId: string,
  obligationId: string,
): Promise<ObligationOut> {
  return api<ObligationOut>(
    `${BASE}/projects/${projectId}/obligations/${obligationId}`,
  );
}

export function updateObligation(
  projectId: string,
  obligationId: string,
  body: UpdateObligationBody,
): Promise<ObligationOut> {
  return api<ObligationOut>(
    `${BASE}/projects/${projectId}/obligations/${obligationId}`,
    { method: "PATCH", json: body },
  );
}

export function startObligation(
  projectId: string,
  obligationId: string,
): Promise<ObligationOut> {
  return api<ObligationOut>(
    `${BASE}/projects/${projectId}/obligations/${obligationId}/start`,
    { method: "POST", json: {} },
  );
}

export function completeObligation(
  projectId: string,
  obligationId: string,
): Promise<ObligationOut> {
  return api<ObligationOut>(
    `${BASE}/projects/${projectId}/obligations/${obligationId}/complete`,
    { method: "POST", json: {} },
  );
}

export function verifyObligation(
  projectId: string,
  obligationId: string,
): Promise<ObligationOut> {
  return api<ObligationOut>(
    `${BASE}/projects/${projectId}/obligations/${obligationId}/verify`,
    { method: "POST", json: {} },
  );
}
