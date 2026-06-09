/**
 * API client cliente · Cloud Remediations approval workflow (Bloque 3+5).
 *
 * Endpoints cliente portal (require_client_user):
 *   GET  /api/v1/client-portal/cloud-gaps              list pending propuestas
 *   POST /api/v1/client-portal/cloud-gaps/{gid}/approve
 *   POST /api/v1/client-portal/cloud-gaps/{gid}/reject
 *
 * ADR-013 doble pool · cliente endpoints separate del admin pool.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/client-portal/cloud-gaps";

export type RemediationApprovalStatus =
  | "detected"
  | "proposed_to_cliente"
  | "approved"
  | "rejected"
  | "executing"
  | "executed"
  | "failed";

export type RemediationSeverity = "critical" | "high" | "medium" | "low";

export interface RemediationGap {
  id: string;
  project_id: string;
  ens_measure_code: string;
  severity: RemediationSeverity | string;
  title: string;
  explanation_es: string | null;
  suggested_action: string | null;
  approval_status: RemediationApprovalStatus | string;
  proposed_to_cliente_at: string | null;
  cliente_approval_at: string | null;
  resolved_at: string | null;
  evidence_link_id: string | null;
}

export interface RemediationListResponse {
  project_id: string | null;
  count: number;
  gaps: RemediationGap[];
}

export interface RemediationActionResponse {
  gap_id: string;
  approval_status: string;
  friendly_message?: string;
}

export const REMEDIATION_STATUS_LABELS: Record<
  RemediationApprovalStatus,
  string
> = {
  detected: "Detectado",
  proposed_to_cliente: "Pendiente de tu decisión",
  approved: "Aprobado · Marcos preparando",
  rejected: "Rechazado",
  executing: "Marcos lo está aplicando",
  executed: "¡Hecho! Ya está aplicado",
  failed: "Hubo un problema · Marcos lo revisa",
};

export const REMEDIATION_STATUS_VARIANTS: Record<
  RemediationApprovalStatus,
  "secondary" | "warning" | "success" | "danger" | "outline"
> = {
  detected: "outline",
  proposed_to_cliente: "warning",
  approved: "secondary",
  rejected: "outline",
  executing: "secondary",
  executed: "success",
  failed: "danger",
};

export const SEVERITY_LABELS: Record<RemediationSeverity, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Media",
  low: "Baja",
};

export const SEVERITY_VARIANTS: Record<
  RemediationSeverity,
  "danger" | "warning" | "secondary" | "outline"
> = {
  critical: "danger",
  high: "warning",
  medium: "secondary",
  low: "outline",
};

export const clientCloudRemediationsApi = {
  list: () => api<RemediationListResponse>(BASE),

  approve: (gapId: string, notes?: string) =>
    api<RemediationActionResponse>(`${BASE}/${gapId}/approve`, {
      json: { notes: notes ?? null },
    }),

  reject: (gapId: string, notes?: string) =>
    api<RemediationActionResponse>(`${BASE}/${gapId}/reject`, {
      json: { notes: notes ?? null },
    }),
};
