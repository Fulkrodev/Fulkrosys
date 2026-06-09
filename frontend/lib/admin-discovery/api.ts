"use client";

/**
 * Admin Discovery API client (SAN-E v3.MB-4.1).
 *
 * Wraps Motor 22 endpoints (37 totales bajo /api/v1/projects/{id}).
 * 12 sub-features backend → 8 tabs UX consolidados.
 *
 * Backend dict shapes deriva de:
 *   backend/app/models/discovery.py (DiscoveryRun · Alert · Configuration ·
 *     VulnerabilityFinding · DataStore · LoggingAssessment · DataFlow ·
 *     ContinuityAssessment)
 *   backend/app/models/onboarding.py (DiscoveredAsset · DiscoveredIdentity)
 */

import { api } from "@/lib/api";

// =====================================================================
// Common
// =====================================================================

export type Severidad = "critical" | "high" | "medium" | "low" | "info";

// =====================================================================
// DiscoveryRun
// =====================================================================

export interface DiscoveryRun {
  id: string;
  project_id: string;
  modules: string[];
  connector_sources: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  error_details: string | null;
  triggered_by: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateRunBody {
  modules?: string[];
  connector_sources?: Record<string, unknown>;
  triggered_by?: string;
  execute?: boolean;
}

// =====================================================================
// Tab 1 · Assets
// =====================================================================

export interface DiscoveryAsset {
  id: string;
  project_id: string;
  discovery_run_id: string | null;
  fuente_conector: string | null;
  tipo_magerit: string | null;
  nombre: string;
  identificador: string | null;
  descripcion: string | null;
  criticidad_propuesta: string | null;
  propietario_inferido: string | null;
  ubicacion: string | null;
  metadata_extra: Record<string, unknown>;
  pkg_node_id: string | null;
  created_at: string | null;
}

export interface AssetsSummary {
  total: number;
  por_tipo_magerit: Record<string, number>;
  por_criticidad: Record<string, number>;
  por_fuente: Record<string, number>;
  ultima_descubierta: string | null;
}

// =====================================================================
// Tab 2 · Identity
// =====================================================================

export interface DiscoveryIdentity {
  id: string;
  project_id: string;
  discovery_run_id: string | null;
  fuente_conector: string | null;
  directorio: string | null;
  username: string | null;
  email: string | null;
  display_name: string | null;
  tipo_cuenta: string | null;
  es_privilegiada: boolean | null;
  es_activa: boolean | null;
  mfa_activo: boolean | null;
  dias_inactiva: number | null;
  password_policy_compliant: boolean | null;
  grupos: unknown[];
  permisos_efectivos: unknown[];
  alertas: unknown[];
  pkg_node_id: string | null;
  created_at: string | null;
}

export interface IdentitiesSummary {
  total: number;
  privilegiadas: number;
  inactivas: number;
  sin_mfa: number;
  por_tipo_cuenta: Record<string, number>;
}

// =====================================================================
// Tab 3 · Data Stores
// =====================================================================

export interface DiscoveryDataStore {
  id: string;
  project_id: string;
  discovery_run_id: string;
  fuente_conector: string;
  tipo: string;
  nombre: string;
  ubicacion: string;
  volumen_estimado_gb: number | null;
  clasificacion_inicial: string;
  patrones_detectados: string[];
  tiene_datos_personales: boolean | null;
  tiene_datos_salud: boolean | null;
  tiene_datos_financieros: boolean | null;
  cifrado_en_reposo: boolean | null;
  cifrado_en_transito: boolean | null;
  control_acceso: string | null;
  tiene_backup: boolean | null;
  metadata_extra: Record<string, unknown>;
  pkg_node_id: string | null;
  created_at: string | null;
}

export interface DataStoresSummary {
  total: number;
  con_datos_personales: number;
  con_datos_salud: number;
  con_datos_financieros: number;
  por_clasificacion: Record<string, number>;
}

// =====================================================================
// Tab 4 · Vulnerabilities
// =====================================================================

export interface DiscoveryVulnerability {
  id: string;
  project_id: string;
  discovery_run_id: string;
  fuente: string;
  titulo: string;
  descripcion: string | null;
  cve_id: string | null;
  cvss_score: number | null;
  cvss_vector: string | null;
  cvss_severity: Severidad | null;
  asset_afectado: string | null;
  asset_id: string | null;
  es_explotable: boolean | null;
  exploit_disponible: boolean | null;
  remediacion_sugerida: string | null;
  medidas_ens_afectadas: string[];
  mitre_tactics: string[];
  estado: "open" | "mitigated" | "accepted" | "false_positive";
  created_at: string | null;
}

export interface VulnsSummary {
  total: number;
  por_severidad: Record<string, number>;
  por_estado: Record<string, number>;
  explotables: number;
}

export interface VulnUpdateBody {
  estado?: "open" | "mitigated" | "accepted" | "false_positive";
  remediacion_sugerida?: string;
}

export interface VulnImportBody {
  run_id: string;
  fuente: string;
  findings: unknown[];
}

// =====================================================================
// Tab 5 · Configurations
// =====================================================================

export interface DiscoveryConfig {
  id: string;
  project_id: string;
  discovery_run_id: string;
  fuente_conector: string;
  sistema: string;
  control_id: string;
  control_description: string | null;
  estado: "pass" | "fail" | "warn" | "n/a";
  valor_actual: string | null;
  valor_esperado: string | null;
  gap_severidad: Severidad | null;
  herramienta_deteccion: string;
  medidas_ens_afectadas: string[];
  raw_output: Record<string, unknown>;
  created_at: string | null;
}

export interface ConfigsSummary {
  total: number;
  pass: number;
  fail: number;
  warn: number;
  por_severidad: Record<string, number>;
}

// =====================================================================
// Tab 6 · Data Flow
// =====================================================================

export interface DataFlowDiagram {
  id: string;
  project_id: string;
  discovery_run_id: string;
  nombre: string;
  descripcion: string | null;
  tipo: string;
  nodos: Array<Record<string, unknown>>;
  flujos: Array<Record<string, unknown>>;
  clasificacion_max_datos: string;
  mermaid_code: string | null;
  observaciones_seguridad: Array<Record<string, unknown>>;
  created_at: string | null;
}

export interface GenerateDataflowBody {
  run_id: string;
}

// =====================================================================
// Tab 7 · Continuity
// =====================================================================

export interface ContinuityAssessment {
  id: string;
  project_id: string;
  discovery_run_id: string;
  backups_inventario: Array<Record<string, unknown>>;
  tiene_backup_offsite: boolean | null;
  tiene_backup_cifrado: boolean | null;
  ultima_prueba_restauracion: string | null;
  prueba_restauracion_exitosa: boolean | null;
  tiene_drp: boolean | null;
  drp_documentado: boolean | null;
  drp_probado: boolean | null;
  drp_ultima_prueba: string | null;
  slas_proveedores: Array<Record<string, unknown>>;
  spofs_detectados: Array<Record<string, unknown>>;
  rto_global_horas: number | null;
  rpo_global_horas: number | null;
  nivel_madurez_continuidad: string;
  observaciones: string | null;
  created_at: string | null;
}

export interface ContinuityBody {
  run_id: string;
  continuity_data?: Record<string, unknown>;
}

// =====================================================================
// Tab 8 · Logging
// =====================================================================

export interface LoggingAssessment {
  id: string;
  project_id: string;
  discovery_run_id: string;
  tiene_siem: boolean | null;
  siem_producto: string | null;
  fuentes_log: string[];
  cobertura: {
    servidores: number | null;
    red: number | null;
    aplicaciones: number | null;
    endpoints: number | null;
  };
  retencion_minima_dias: number | null;
  retencion_maxima_dias: number | null;
  cumple_retencion_ens: boolean | null;
  tiene_alertas_activas: boolean | null;
  alertas_revisadas_por: string | null;
  casos_uso_activos: number | null;
  cumple_op_exp_8: boolean | null;
  gaps_op_exp_8: string[];
  nivel_madurez_logging: string;
  observaciones: string | null;
  created_at: string | null;
}

export interface LoggingBody {
  run_id: string;
  logging_data?: Record<string, unknown>;
}

// =====================================================================
// Alerts (deterministic findings cross-module)
// =====================================================================

export interface DiscoveryAlert {
  id: string;
  project_id: string;
  discovery_run_id: string;
  modulo: string;
  severidad: Severidad;
  codigo: string;
  titulo: string;
  descripcion: string;
  entity_type: string;
  entity_id: string;
  medidas_ens_afectadas: string[];
  gap_volcado: boolean;
  created_at: string | null;
}

export interface AlertsSummary {
  total: number;
  por_severidad: Record<string, number>;
  por_modulo: Record<string, number>;
  con_gap_volcado: number;
}

// =====================================================================
// Motor-wide summary (shown in panel header)
// =====================================================================

export interface DiscoverySummary {
  assets_total: number;
  identities_total: number;
  data_stores_total: number;
  vulnerabilities_total: number;
  configurations_total: number;
  dataflows_total: number;
  alerts_total: number;
  last_run_at: string | null;
  last_run_status: string | null;
}

// =====================================================================
// API functions
// =====================================================================

const BASE = "/api/v1/projects";

// -------- Runs --------
export async function listDiscoveryRuns(projectId: string): Promise<DiscoveryRun[]> {
  return api<DiscoveryRun[]>(`${BASE}/${projectId}/runs`);
}

export async function createDiscoveryRun(
  projectId: string,
  body: CreateRunBody = {},
): Promise<DiscoveryRun> {
  return api<DiscoveryRun>(`${BASE}/${projectId}/runs`, {
    method: "POST",
    json: body,
  });
}

export async function cancelDiscoveryRun(
  projectId: string,
  runId: string,
): Promise<DiscoveryRun> {
  return api<DiscoveryRun>(`${BASE}/${projectId}/runs/${runId}/cancel`, {
    method: "POST",
  });
}

// -------- Summary --------
export async function getDiscoverySummary(projectId: string): Promise<DiscoverySummary> {
  return api<DiscoverySummary>(`${BASE}/${projectId}/summary`);
}

// -------- Assets --------
export async function listDiscoveryAssets(
  projectId: string,
  filters?: { tipo_magerit?: string; criticidad?: string; fuente?: string },
): Promise<DiscoveryAsset[]> {
  const qs = new URLSearchParams();
  if (filters?.tipo_magerit) qs.set("tipo_magerit", filters.tipo_magerit);
  if (filters?.criticidad) qs.set("criticidad", filters.criticidad);
  if (filters?.fuente) qs.set("fuente", filters.fuente);
  const suffix = qs.toString() ? `?${qs}` : "";
  return api<DiscoveryAsset[]>(`${BASE}/${projectId}/assets${suffix}`);
}

export async function getAssetsSummary(projectId: string): Promise<AssetsSummary> {
  return api<AssetsSummary>(`${BASE}/${projectId}/assets/summary`);
}

export async function deleteAsset(projectId: string, assetId: string): Promise<void> {
  await api<{ deleted: boolean }>(`${BASE}/${projectId}/assets/${assetId}`, {
    method: "DELETE",
  });
}

// -------- Identities --------
export async function listDiscoveryIdentities(
  projectId: string,
  filters?: { directorio?: string; tipo_cuenta?: string },
): Promise<DiscoveryIdentity[]> {
  const qs = new URLSearchParams();
  if (filters?.directorio) qs.set("directorio", filters.directorio);
  if (filters?.tipo_cuenta) qs.set("tipo_cuenta", filters.tipo_cuenta);
  const suffix = qs.toString() ? `?${qs}` : "";
  return api<DiscoveryIdentity[]>(`${BASE}/${projectId}/identities${suffix}`);
}

export async function getIdentitiesSummary(projectId: string): Promise<IdentitiesSummary> {
  return api<IdentitiesSummary>(`${BASE}/${projectId}/identities/summary`);
}

// -------- Data Stores --------
export async function listDiscoveryDataStores(
  projectId: string,
  filters?: { clasificacion?: string; fuente?: string },
): Promise<DiscoveryDataStore[]> {
  const qs = new URLSearchParams();
  if (filters?.clasificacion) qs.set("clasificacion", filters.clasificacion);
  if (filters?.fuente) qs.set("fuente", filters.fuente);
  const suffix = qs.toString() ? `?${qs}` : "";
  return api<DiscoveryDataStore[]>(`${BASE}/${projectId}/data-stores${suffix}`);
}

export async function getDataStoresSummary(projectId: string): Promise<DataStoresSummary> {
  return api<DataStoresSummary>(`${BASE}/${projectId}/data-stores/summary`);
}

// -------- Vulnerabilities --------
export async function listDiscoveryVulns(
  projectId: string,
  filters?: { severidad?: string; estado?: string },
): Promise<DiscoveryVulnerability[]> {
  const qs = new URLSearchParams();
  if (filters?.severidad) qs.set("severidad", filters.severidad);
  if (filters?.estado) qs.set("estado", filters.estado);
  const suffix = qs.toString() ? `?${qs}` : "";
  return api<DiscoveryVulnerability[]>(`${BASE}/${projectId}/vulnerabilities${suffix}`);
}

export async function getVulnsSummary(projectId: string): Promise<VulnsSummary> {
  return api<VulnsSummary>(`${BASE}/${projectId}/vulnerabilities/summary`);
}

export async function updateVulnerability(
  projectId: string,
  findingId: string,
  body: VulnUpdateBody,
): Promise<DiscoveryVulnerability> {
  return api<DiscoveryVulnerability>(
    `${BASE}/${projectId}/vulnerabilities/${findingId}`,
    { method: "PATCH", json: body },
  );
}

// -------- Configurations --------
export async function listDiscoveryConfigs(
  projectId: string,
  filters?: { gap_severidad?: string; fuente?: string; estado?: string },
): Promise<DiscoveryConfig[]> {
  const qs = new URLSearchParams();
  if (filters?.gap_severidad) qs.set("gap_severidad", filters.gap_severidad);
  if (filters?.fuente) qs.set("fuente", filters.fuente);
  if (filters?.estado) qs.set("estado", filters.estado);
  const suffix = qs.toString() ? `?${qs}` : "";
  return api<DiscoveryConfig[]>(`${BASE}/${projectId}/configurations${suffix}`);
}

export async function getConfigsSummary(projectId: string): Promise<ConfigsSummary> {
  return api<ConfigsSummary>(`${BASE}/${projectId}/configurations/summary`);
}

// -------- Data Flows --------
export async function listDataFlows(projectId: string): Promise<DataFlowDiagram[]> {
  return api<DataFlowDiagram[]>(`${BASE}/${projectId}/dataflows`);
}

export async function generateDataFlows(
  projectId: string,
  body: GenerateDataflowBody,
): Promise<{ generated: number; dfds: DataFlowDiagram[] }> {
  return api<{ generated: number; dfds: DataFlowDiagram[] }>(
    `${BASE}/${projectId}/dataflows/generate`,
    { method: "POST", json: body },
  );
}

// -------- Continuity --------
export async function getContinuityAssessment(
  projectId: string,
): Promise<ContinuityAssessment | null> {
  return api<ContinuityAssessment | null>(`${BASE}/${projectId}/continuity`);
}

export async function recordContinuityAssessment(
  projectId: string,
  body: ContinuityBody,
): Promise<ContinuityAssessment> {
  return api<ContinuityAssessment>(`${BASE}/${projectId}/continuity`, {
    method: "POST",
    json: body,
  });
}

// -------- Logging --------
export async function getLoggingAssessment(
  projectId: string,
): Promise<LoggingAssessment | null> {
  return api<LoggingAssessment | null>(`${BASE}/${projectId}/logging`);
}

export async function recordLoggingAssessment(
  projectId: string,
  body: LoggingBody,
): Promise<LoggingAssessment> {
  return api<LoggingAssessment>(`${BASE}/${projectId}/logging`, {
    method: "POST",
    json: body,
  });
}

// -------- Alerts (cross-tab) --------
export async function listDiscoveryAlerts(
  projectId: string,
  filters?: { severidad?: string; modulo?: string; run_id?: string },
): Promise<DiscoveryAlert[]> {
  const qs = new URLSearchParams();
  if (filters?.severidad) qs.set("severidad", filters.severidad);
  if (filters?.modulo) qs.set("modulo", filters.modulo);
  if (filters?.run_id) qs.set("run_id", filters.run_id);
  const suffix = qs.toString() ? `?${qs}` : "";
  return api<DiscoveryAlert[]>(`${BASE}/${projectId}/alerts${suffix}`);
}

export async function getAlertsSummary(projectId: string): Promise<AlertsSummary> {
  return api<AlertsSummary>(`${BASE}/${projectId}/alerts/summary`);
}
