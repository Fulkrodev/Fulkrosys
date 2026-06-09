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

export type DriftSeverity = "CRITICA" | "ALTA" | "MEDIA" | "BAJA";

export type DriftDimension =
  | "auth"
  | "cifrado"
  | "backups"
  | "monitoring"
  | "personal"
  | "proveedores"
  | "acceso"
  | "fisico"
  | "contingencia"
  | "auditoria";

export const DRIFT_DIMENSIONS: DriftDimension[] = [
  "auth",
  "cifrado",
  "backups",
  "monitoring",
  "personal",
  "proveedores",
  "acceso",
  "fisico",
  "contingencia",
  "auditoria",
];

export const DRIFT_SEVERITIES: DriftSeverity[] = [
  "CRITICA",
  "ALTA",
  "MEDIA",
  "BAJA",
];

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
