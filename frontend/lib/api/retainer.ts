/**
 * Motor 23 — Retainer Management API client.
 *
 * 31 endpoints reales (zero-mock):
 *   • 22 endpoints en `/retainer` (api.py)
 *   • 9 endpoints en `/retainer/paso2` (api_paso2.py)
 *
 * Tipos espejo de los Pydantic schemas + serializers en
 * `backend/app/motors/m23_retainer/`. RetainerPlan amplía a los 5 tiers
 * reales del backend (R_MICRO/R_LITE/R_STD/R_PLUS/R_CRITICAL).
 *
 * Usa `api()` wrapper con CSRF + credentials.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

// ═══════════════════════════════════════════════════════════════════
// Tipos compartidos
// ═══════════════════════════════════════════════════════════════════

export type RetainerTier =
  | "R_MICRO"
  | "R_LITE"
  | "R_STD"
  | "R_PLUS"
  | "R_CRITICAL";

// #33 · Tiers comerciales (de cara al cliente). Los 5 técnicos de arriba siguen
// siendo la fuente de verdad del backend; esto es solo presentación.
export type CommercialTier = "R_BÁSICO" | "R_MEDIO" | "R_ALTO";

export const TIER_COMMERCIAL_LABELS: Record<RetainerTier, CommercialTier> = {
  R_MICRO: "R_BÁSICO",
  R_LITE: "R_BÁSICO",
  R_STD: "R_MEDIO",
  R_PLUS: "R_ALTO",
  R_CRITICAL: "R_ALTO",
};

export function getCommercialTier(tier: RetainerTier): CommercialTier {
  return TIER_COMMERCIAL_LABELS[tier];
}

export type RetainerEstado =
  | "active"
  | "paused"
  | "cancelled"
  | "expired"
  | "draft";

export type RagStatus = "green" | "amber" | "red";

export type RenewalStatus =
  | "ok"
  | "warning"
  | "urgent"
  | "overdue"
  | null;

export type ActivityEstado =
  | "programada"
  | "en_curso"
  | "completada"
  | "cancelada";

export type DriftEstado = "abierto" | "en_revision" | "resuelto";

// ─── Profiles & catalogs ───────────────────────────────────────────

export interface ProfileSummary {
  codigo: string;
  sla_respuesta_horas: number;
  horas_previstas_anual: number;
  actividades: string[];
}

export interface ProfilesResponse {
  profiles: ProfileSummary[];
}

export interface ProfileCadencesResponse {
  profile: string;
  sla_respuesta_horas: number;
  horas_previstas_anual: number;
  cadencias: Record<string, { frecuencia: string; meses?: number[] }>;
}

export interface DriftCatalogResponse {
  dimensions: string[];
  severities: string[];
  impacts: string[];
}

// ─── Retainer entity ───────────────────────────────────────────────

export interface RetainerSummary {
  id: string;
  client_id: string | null;
  project_id: string | null;
  contract_id: string | null;
  perfil: string;
  modalidad: string;
  precio_mensual: number | null;
  inicio: string | null;
  fin: string | null;
  renovacion_automatica: boolean;
  sla_respuesta_horas: number | null;
  estado: RetainerEstado;
  next_renewal_date: string | null;
  renewal_status: RenewalStatus;
  rag_status: RagStatus | null;
  horas_consumidas_total: number;
  horas_previstas_anual: number;
  created_at: string | null;
}

export interface RetainerActivityRecord {
  id: string;
  retainer_contract_id: string;
  project_id: string | null;
  tipo_actividad: string;
  titulo: string | null;
  descripcion: string | null;
  fecha_programada: string | null;
  fecha_ejecutada: string | null;
  estado: ActivityEstado;
  horas_estimadas: number;
  horas_consumidas: number;
  resultado: string | null;
  prioridad: string | null;
}

export interface RetainerDriftRecord {
  id: string;
  retainer_contract_id: string;
  project_id: string;
  dimension: string;
  descripcion: string;
  severidad: string;
  impacto: string;
  estado: DriftEstado;
  resuelto_at: string | null;
  created_at: string | null;
}

// ─── Dashboard global (legacy /retainer/dashboard) ─────────────────

export interface RetainerDashboardResponse {
  // Forma libre del retainer_service.get_dashboard;
  // se consume vía useRetainerDashboard cuando sea relevante.
  [key: string]: unknown;
}

// ─── Paso 2 ────────────────────────────────────────────────────────

export interface NextActivityRef {
  tipo: string;
  titulo: string | null;
  fecha: string | null;
  countdown_days: number | null;
}

export interface RetainerOverviewItem {
  retainer_id: string;
  client_id: string;
  client_name: string;
  tier: string;
  monthly_fee: number;
  health_status: RagStatus;
  rag_status_db: RagStatus | null;
  next_activity: NextActivityRef | null;
  cert_renewal_date: string | null;
  days_until_renewal: number | null;
  renewal_status: RenewalStatus;
}

export interface Agent26AlertItem {
  retainer_contract_id: string;
  client_name: string;
  tier: string;
  priority: "critical" | "high" | "medium" | "low";
  code: string;
  title: string;
  description: string;
  suggested_action: string;
  metadata: Record<string, unknown>;
}

export interface Agent26Summary {
  total_alerts: number;
  by_priority: Record<string, number>;
  top_alerts: Agent26AlertItem[];
  generated_at: string;
  [k: string]: unknown;
}

export interface RetainerPaso2Dashboard {
  retainers: RetainerOverviewItem[];
  mrr_total: number;
  total_retainers: number;
  agent_26_summary: Agent26Summary;
  generated_at: string;
}

export interface TimelineEvent {
  uid: string;
  summary: string;
  description: string;
  dtstart: string | null;
  status: ActivityEstado;
  priority: string | null;
  categories: string[];
  horas_estimadas: number;
}

export interface RetainerTimelineResponse {
  retainer_id: string;
  tier: string;
  events: TimelineEvent[];
  total_events: number;
}

export interface HealthDetail {
  health: RagStatus;
  rag_db: RagStatus | null;
  signals: Record<string, unknown>;
  [k: string]: unknown;
}

export interface PricingCatalogEntry {
  category: string;
  tier_code: string;
  name: string;
  base_price: number;
  currency: string;
  billing_unit: string;
  extras_jsonb: Record<string, unknown> | null;
  description: string | null;
}

export interface SuggestTierResponse {
  recommended_tier: string;
  confidence: number;
  rationale?: string;
  alternatives?: string[];
  [k: string]: unknown;
}

export interface UpgradeResponse {
  retainer_id: string;
  upgraded_from: { tier: string; price: number };
  upgraded_to: { tier: string; price: number };
}

export interface MaterialChangeResponse {
  activity_id: string;
  fecha_programada: string | null;
  titulo: string | null;
}

// ─── Renewal ────────────────────────────────────────────────────────

export interface RenewalStatusResponse {
  retainer_id: string;
  next_renewal_date: string | null;
  renewal_status: RenewalStatus;
}

export interface RagRecalcResponse {
  retainer_id: string;
  rag_status: RagStatus | null;
}

// ─── Activities responses ──────────────────────────────────────────

export interface ActivitiesListResponse {
  activities: RetainerActivityRecord[];
}

export interface GenerateActivitiesResponse {
  year: number;
  count: number;
  activities: RetainerActivityRecord[];
}

export interface DriftsListResponse {
  drifts: RetainerDriftRecord[];
}

export interface RetainersListResponse {
  retainers: RetainerSummary[];
}

// ─── Bodies ────────────────────────────────────────────────────────

export interface CreateRetainerBody {
  client_id: string;
  perfil?: string;
  precio_mensual: number;
  inicio: string; // YYYY-MM-DD
  fin?: string | null;
  contract_id?: string | null;
  next_renewal_date?: string | null;
  modalidad?: string;
}

export interface UpdateRetainerBody {
  perfil?: string;
  precio_mensual?: number;
  fin?: string | null;
  renovacion_automatica?: boolean;
  estado?: RetainerEstado;
}

export interface GenerateActivitiesBody {
  year: number;
}

export interface CompleteActivityBody {
  horas_consumidas: number;
  resultado?: string;
}

export interface RenewBody {
  new_renewal_date: string; // YYYY-MM-DD
}

export interface RegisterDriftBody {
  dimension: string;
  descripcion: string;
  severidad: string;
  impacto: string;
}

export interface SuggestTierBody {
  categoria: "BASICA" | "MEDIA" | "ALTA";
  empleados: number;
  sector?: string;
  ubicaciones?: number;
  datos_sensibles?: boolean;
}

export interface MaterialChangeBody {
  change_description: string;
  urgent?: boolean;
}

// ═══════════════════════════════════════════════════════════════════
// /retainer (api.py — 22 endpoints)
// ═══════════════════════════════════════════════════════════════════

// ─── Catálogos ──────────────────────────────────────────────────────

export async function listProfiles(): Promise<ProfilesResponse> {
  return api<ProfilesResponse>(`${BASE}/retainer/profiles`);
}

export async function getProfileCadences(
  profile: string,
): Promise<ProfileCadencesResponse> {
  return api<ProfileCadencesResponse>(
    `${BASE}/retainer/profiles/${encodeURIComponent(profile)}/cadences`,
  );
}

export async function getDriftCatalog(): Promise<DriftCatalogResponse> {
  return api<DriftCatalogResponse>(`${BASE}/retainer/drift-catalog`);
}

// ─── Dashboard / listing ────────────────────────────────────────────

export async function getRetainerDashboard(): Promise<RetainerDashboardResponse> {
  return api<RetainerDashboardResponse>(`${BASE}/retainer/dashboard`);
}

export interface ListRetainersFilters {
  estado?: string;
  perfil?: string;
  rag?: string;
}

export async function listRetainers(
  filters: ListRetainersFilters = {},
): Promise<RetainersListResponse> {
  const qs = new URLSearchParams();
  if (filters.estado) qs.set("estado", filters.estado);
  if (filters.perfil) qs.set("perfil", filters.perfil);
  if (filters.rag) qs.set("rag", filters.rag);
  const q = qs.toString();
  return api<RetainersListResponse>(
    `${BASE}/retainer/list${q ? `?${q}` : ""}`,
  );
}

// ─── Lifecycle por proyecto ─────────────────────────────────────────

export async function createRetainer(
  projectId: string,
  body: CreateRetainerBody,
): Promise<RetainerSummary> {
  return api<RetainerSummary>(
    `${BASE}/retainer/projects/${projectId}/retainer`,
    { json: body },
  );
}

export async function getProjectRetainer(
  projectId: string,
): Promise<RetainerSummary> {
  return api<RetainerSummary>(
    `${BASE}/retainer/projects/${projectId}/retainer`,
  );
}

export async function updateProjectRetainer(
  projectId: string,
  body: UpdateRetainerBody,
): Promise<RetainerSummary> {
  return api<RetainerSummary>(
    `${BASE}/retainer/projects/${projectId}/retainer`,
    { method: "PATCH", json: body },
  );
}

export async function pauseProjectRetainer(
  projectId: string,
): Promise<RetainerSummary> {
  return api<RetainerSummary>(
    `${BASE}/retainer/projects/${projectId}/retainer/pause`,
    { json: {} },
  );
}

export async function cancelProjectRetainer(
  projectId: string,
): Promise<RetainerSummary> {
  return api<RetainerSummary>(
    `${BASE}/retainer/projects/${projectId}/retainer/cancel`,
    { json: {} },
  );
}

// ─── Activities ─────────────────────────────────────────────────────

export async function generateActivities(
  projectId: string,
  body: GenerateActivitiesBody,
): Promise<GenerateActivitiesResponse> {
  return api<GenerateActivitiesResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/activities/generate`,
    { json: body },
  );
}

export interface ListActivitiesFilters {
  tipo?: string;
  estado?: string;
  desde?: string; // YYYY-MM-DD
  hasta?: string;
}

export async function listActivities(
  projectId: string,
  filters: ListActivitiesFilters = {},
): Promise<ActivitiesListResponse> {
  const qs = new URLSearchParams();
  if (filters.tipo) qs.set("tipo", filters.tipo);
  if (filters.estado) qs.set("estado", filters.estado);
  if (filters.desde) qs.set("desde", filters.desde);
  if (filters.hasta) qs.set("hasta", filters.hasta);
  const q = qs.toString();
  return api<ActivitiesListResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/activities${q ? `?${q}` : ""}`,
  );
}

export async function startActivity(
  projectId: string,
  activityId: string,
): Promise<RetainerActivityRecord> {
  return api<RetainerActivityRecord>(
    `${BASE}/retainer/projects/${projectId}/retainer/activities/${activityId}/start`,
    { json: {} },
  );
}

export async function completeActivity(
  projectId: string,
  activityId: string,
  body: CompleteActivityBody,
): Promise<RetainerActivityRecord> {
  return api<RetainerActivityRecord>(
    `${BASE}/retainer/projects/${projectId}/retainer/activities/${activityId}/complete`,
    { json: body },
  );
}

export async function listOverdueActivities(
  projectId: string,
): Promise<ActivitiesListResponse> {
  return api<ActivitiesListResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/activities/overdue`,
  );
}

// ─── Renewal ────────────────────────────────────────────────────────

export async function getRenewalStatus(
  projectId: string,
): Promise<RenewalStatusResponse> {
  return api<RenewalStatusResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/renewal-status`,
  );
}

export async function renewProjectRetainer(
  projectId: string,
  body: RenewBody,
): Promise<RetainerSummary> {
  return api<RetainerSummary>(
    `${BASE}/retainer/projects/${projectId}/retainer/renew`,
    { json: body },
  );
}

// ─── Drift ──────────────────────────────────────────────────────────

export async function registerDrift(
  projectId: string,
  body: RegisterDriftBody,
): Promise<RetainerDriftRecord> {
  return api<RetainerDriftRecord>(
    `${BASE}/retainer/projects/${projectId}/retainer/drifts`,
    { json: body },
  );
}

export interface ListDriftsFilters {
  severidad?: string;
  estado?: string;
}

export async function listDrifts(
  projectId: string,
  filters: ListDriftsFilters = {},
): Promise<DriftsListResponse> {
  const qs = new URLSearchParams();
  if (filters.severidad) qs.set("severidad", filters.severidad);
  if (filters.estado) qs.set("estado", filters.estado);
  const q = qs.toString();
  return api<DriftsListResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/drifts${q ? `?${q}` : ""}`,
  );
}

export async function resolveDrift(
  projectId: string,
  driftId: string,
): Promise<RetainerDriftRecord> {
  return api<RetainerDriftRecord>(
    `${BASE}/retainer/projects/${projectId}/retainer/drifts/${driftId}/resolve`,
    { json: {} },
  );
}

export async function recalculateRag(
  projectId: string,
): Promise<RagRecalcResponse> {
  return api<RagRecalcResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/rag/recalculate`,
    { json: {} },
  );
}

// ─── Billing ────────────────────────────────────────────────────────

export interface MonthlyInvoiceResponse {
  invoice_id?: string;
  amount?: number;
  status?: string;
  [k: string]: unknown;
}

export async function generateMonthlyInvoice(
  projectId: string,
): Promise<MonthlyInvoiceResponse> {
  return api<MonthlyInvoiceResponse>(
    `${BASE}/retainer/projects/${projectId}/retainer/generate-monthly-invoice`,
    { json: {} },
  );
}

// ═══════════════════════════════════════════════════════════════════
// /retainer/paso2 (api_paso2.py — 9 endpoints)
// ═══════════════════════════════════════════════════════════════════

export async function getPaso2Dashboard(): Promise<RetainerPaso2Dashboard> {
  return api<RetainerPaso2Dashboard>(`${BASE}/retainer/paso2/dashboard`);
}

export async function getRetainerTimeline(
  retainerId: string,
): Promise<RetainerTimelineResponse> {
  return api<RetainerTimelineResponse>(
    `${BASE}/retainer/paso2/${retainerId}/timeline`,
  );
}

export async function getHealthDetail(
  retainerId: string,
): Promise<HealthDetail> {
  return api<HealthDetail>(
    `${BASE}/retainer/paso2/${retainerId}/health-detail`,
  );
}

export async function suggestTier(
  body: SuggestTierBody,
): Promise<SuggestTierResponse> {
  return api<SuggestTierResponse>(
    `${BASE}/retainer/paso2/suggest-tier`,
    { json: body },
  );
}

export async function upgradeTier(
  retainerId: string,
  newTier: RetainerTier,
): Promise<UpgradeResponse> {
  return api<UpgradeResponse>(
    `${BASE}/retainer/paso2/${retainerId}/upgrade?new_tier=${encodeURIComponent(newTier)}`,
    { json: {} },
  );
}

export async function triggerMaterialChange(
  projectId: string,
  body: MaterialChangeBody,
): Promise<MaterialChangeResponse> {
  return api<MaterialChangeResponse>(
    `${BASE}/retainer/paso2/material-change/${projectId}`,
    { json: body },
  );
}

export async function getPricingCatalog(
  category?: string,
): Promise<PricingCatalogEntry[]> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return api<PricingCatalogEntry[]>(
    `${BASE}/retainer/paso2/pricing-catalog${qs}`,
  );
}

export async function getAgent26Summary(): Promise<Agent26Summary> {
  return api<Agent26Summary>(`${BASE}/retainer/paso2/agent-26/summary`);
}

export async function getAgent26Alerts(): Promise<Agent26AlertItem[]> {
  return api<Agent26AlertItem[]>(`${BASE}/retainer/paso2/agent-26/alerts`);
}
