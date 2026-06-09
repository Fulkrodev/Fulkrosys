/**
 * API client admin · Cloud Remediations orchestrator (Bloque 3+5).
 *
 * Endpoints admin (require_owner · project-scoped):
 *   POST  /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/propose-to-cliente
 *   POST  /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/execute
 *   POST  /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/mark-executed
 *   POST  /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/mark-failed
 *   GET   /api/v1/admin/projects/{pid}/cloud-gaps/{gid}/audit-log
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/admin/projects";

export type AdminRemediationActor = "admin" | "cliente" | "system";

export type AdminRemediationLogAction =
  | "proposed_to_cliente"
  | "cliente_approved"
  | "cliente_rejected"
  | "executing"
  | "executed"
  | "failed";

export interface AdminRemediationGap {
  id: string;
  project_id: string;
  ens_measure_code: string;
  severity: string;
  title: string;
  explanation_es: string | null;
  suggested_action: string | null;
  approval_status: string;
  proposed_to_cliente_at: string | null;
  cliente_approval_at: string | null;
  resolved_at: string | null;
  evidence_link_id: string | null;
}

export interface AdminRemediationLog {
  id: string;
  gap_id: string;
  action: AdminRemediationLogAction | string;
  actor_user_id: string | null;
  actor_type: AdminRemediationActor;
  notes: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminAuditLogResponse {
  gap_id: string;
  project_id: string;
  count: number;
  logs: AdminRemediationLog[];
}

export const ADMIN_LOG_ACTION_LABELS: Record<
  AdminRemediationLogAction,
  string
> = {
  proposed_to_cliente: "Propuesto al cliente",
  cliente_approved: "Cliente aprobó",
  cliente_rejected: "Cliente rechazó",
  executing: "En ejecución",
  executed: "Ejecutado",
  failed: "Falló",
};

export const ADMIN_LOG_ACTION_VARIANTS: Record<
  AdminRemediationLogAction,
  "secondary" | "warning" | "success" | "danger" | "outline"
> = {
  proposed_to_cliente: "warning",
  cliente_approved: "success",
  cliente_rejected: "outline",
  executing: "secondary",
  executed: "success",
  failed: "danger",
};

export const adminCloudRemediationsApi = {
  proposeToCliente: (
    projectId: string,
    gapId: string,
    notes?: string,
  ) =>
    api<AdminRemediationGap>(
      `${BASE}/${projectId}/cloud-gaps/${gapId}/propose-to-cliente`,
      { json: { notes: notes ?? null } },
    ),

  execute: (projectId: string, gapId: string, notes?: string) =>
    api<AdminRemediationGap>(
      `${BASE}/${projectId}/cloud-gaps/${gapId}/execute`,
      { json: { notes: notes ?? null } },
    ),

  markExecuted: (
    projectId: string,
    gapId: string,
    body: { evidence_link_id?: string; notes?: string } = {},
  ) =>
    api<AdminRemediationGap>(
      `${BASE}/${projectId}/cloud-gaps/${gapId}/mark-executed`,
      {
        json: {
          evidence_link_id: body.evidence_link_id ?? null,
          notes: body.notes ?? null,
        },
      },
    ),

  markFailed: (
    projectId: string,
    gapId: string,
    body: { error_notes: string; error_metadata?: Record<string, unknown> },
  ) =>
    api<AdminRemediationGap>(
      `${BASE}/${projectId}/cloud-gaps/${gapId}/mark-failed`,
      {
        json: {
          error_notes: body.error_notes,
          error_metadata: body.error_metadata ?? null,
        },
      },
    ),

  auditLog: (projectId: string, gapId: string) =>
    api<AdminAuditLogResponse>(
      `${BASE}/${projectId}/cloud-gaps/${gapId}/audit-log`,
    ),
};
