/**
 * Admin Renewal API client (SAN-E v3.MB-3.4).
 *
 * Wired al backend M27 renewal extensions (commit MB-3.D 4a17834) +
 * M28 role-topology + drift (commit MB-3.E 6daaae2):
 *   GET  /api/v1/projects/{id}/renewal/timeline      M27
 *   POST /api/v1/projects/{id}/renewal/contact-auditor M27
 *   GET  /api/v1/projects/{id}/renewal/auditor-info   M27
 *   GET  /api/v1/projects/{id}/drift-summary          M28
 */
import { api } from "@/lib/api";

export type MilestoneStatus =
  | "pendiente"
  | "en_progreso"
  | "completado"
  | "bloqueado"
  | "no_aplica";

// S28d FIX: los enums DEBEN coincidir con los valores REALES almacenados en
// retainer_drift_events (la matview mv_drift_summary_10x4 es un GROUP BY directo,
// sin mapeo). Antes el frontend usaba auth/cifrado/... + CRITICA/ALTA/... que NO
// existen en BD → cellLookup nunca casaba → la matriz mostraba siempre ceros.
// Fuente: backend m23 retainer_service.DRIFT_DIMENSIONS / DRIFT_SEVERITIES.
export type DriftSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type DriftDimension =
  | "infraestructura"
  | "identidad"
  | "proveedores"
  | "normativa"
  | "overlay"
  | "cpstic"
  | "roles"
  | "continuidad"
  | "evidencias"
  | "contratos";

export const DRIFT_DIMENSIONS: DriftDimension[] = [
  "infraestructura",
  "identidad",
  "proveedores",
  "normativa",
  "overlay",
  "cpstic",
  "roles",
  "continuidad",
  "evidencias",
  "contratos",
];

// Orden de mayor a menor severidad (para columnas de la matriz).
export const DRIFT_SEVERITIES: DriftSeverity[] = [
  "CRITICAL",
  "HIGH",
  "MEDIUM",
  "LOW",
];

export interface DriftEvent {
  id: string;
  dimension: string;
  descripcion: string | null;
  severidad: string;
  impacto: string | null;
  estado: string;
  resuelto_at: string | null;
  created_at: string | null;
}

export interface RenewalMilestone {
  id: string;
  campaign_id: string;
  milestone_code: string;
  label: string;
  due_date: string | null;
  status: MilestoneStatus;
  responsable: string | null;
  completed_at: string | null;
  notes: string | null;
}

export interface RenewalTimelineResponse {
  project_id: string;
  campaign_id: string;
  campaign_type: string;
  scheduled_for: string | null;
  milestones: RenewalMilestone[];
  progress: {
    total: number;
    completed: number;
    completed_pct: number;
  };
}

export interface AuditorInfoResponse {
  project_id: string;
  campaign_id: string;
  campaign_status: string;
  audit_window_due: string | null;
  auditor_contacted: boolean;
  auditor_contacted_at: string | null;
  auditor_contact_notes: string | null;
}

export interface DriftCell {
  dimension: string;
  severidad: string;
  open_count: number;
  closed_count: number;
  total_count: number;
  last_detected: string | null;
}

export interface DriftSummaryResponse {
  project_id: string;
  items: DriftCell[];
  open_total: number;
  open_by_severity: Record<string, number>;
}

export interface ContactAuditorPayload {
  auditor_email: string;
  auditor_name: string;
  audit_entity?: string | null;
  message: string;
}

export interface ContactAuditorResponse {
  milestone_id: string;
  status: MilestoneStatus;
  completed_at: string;
  auditor_email: string;
  next_step: string;
}

const projectBase = (projectId: string) => `/api/v1/projects/${projectId}`;

export function getRenewalTimeline(
  projectId: string,
): Promise<RenewalTimelineResponse> {
  return api<RenewalTimelineResponse>(`${projectBase(projectId)}/renewal/timeline`);
}

export function getAuditorInfo(
  projectId: string,
): Promise<AuditorInfoResponse> {
  return api<AuditorInfoResponse>(`${projectBase(projectId)}/renewal/auditor-info`);
}

export function getDriftSummary(
  projectId: string,
): Promise<DriftSummaryResponse> {
  return api<DriftSummaryResponse>(`${projectBase(projectId)}/drift-summary`);
}

export function contactAuditor(
  projectId: string,
  payload: ContactAuditorPayload,
): Promise<ContactAuditorResponse> {
  return api<ContactAuditorResponse>(
    `${projectBase(projectId)}/renewal/contact-auditor`,
    { method: "POST", json: payload },
  );
}

/**
 * S28d · drill-down de una celda de la matriz: lista los drift events de una
 * (dimension, severidad). Endpoint m23 GET /api/v1/retainer/projects/{id}/retainer/drifts
 * (filtros dimension+severidad+estado · valores idénticos a los de la matview).
 */
export async function listDriftEvents(
  projectId: string,
  opts: { dimension?: string; severidad?: string; estado?: string } = {},
): Promise<DriftEvent[]> {
  const qs = new URLSearchParams();
  if (opts.dimension) qs.set("dimension", opts.dimension);
  if (opts.severidad) qs.set("severidad", opts.severidad);
  if (opts.estado) qs.set("estado", opts.estado);
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await api<{ drifts: DriftEvent[] }>(
    `/api/v1/retainer/projects/${projectId}/retainer/drifts${suffix}`,
  );
  return res.drifts;
}
