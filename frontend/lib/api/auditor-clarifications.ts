/**
 * Auditor portal clarifications API client · CLUSTER 3 Phase C2.3.
 *
 * Wraps backend `/api/v1/public/auditor-portal/{token}/clarifications/*`
 * (auditor) + `/api/v1/admin/projects/{project_id}/audit/clarifications/*` (admin).
 *
 * Clarification = pregunta formal del auditor · admin (Marcos) responde con
 * status workflow (open → in_progress → responded → closed). SSE realtime
 * notification dispatched cuando auditor crea (channel project:{id} event
 * auditor_clarification_new).
 */
import { api } from "@/lib/api";

const PUBLIC_BASE = "/api/v1/public/auditor-portal";
const ADMIN_BASE = "/api/v1/admin/projects";

export type ClarificationTargetType =
  | "general"
  | "evidence"
  | "medida"
  | "magerit_asset"
  | "magerit_threat"
  | "magerit_safeguard"
  | "plan_task"
  | "audit_log_entry";

export type ClarificationPriority = "low" | "normal" | "high" | "urgent";

export type ClarificationStatus =
  | "open"
  | "in_progress"
  | "responded"
  | "closed";

export interface ClarificationOut {
  id: string;
  project_id: string;
  question_text: string;
  linked_target_type: ClarificationTargetType;
  linked_target_id: string | null;
  priority: ClarificationPriority;
  status: ClarificationStatus;
  admin_response: string | null;
  admin_responded_at: string | null;
  admin_responded_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ClarificationListResponse {
  total: number;
  items: ClarificationOut[];
}

export interface ClarificationCreateRequest {
  question_text: string;
  linked_target_type?: ClarificationTargetType;
  linked_target_id?: string | null;
  priority?: ClarificationPriority;
}

export interface AdminClarificationPatchRequest {
  admin_response?: string;
  status?: ClarificationStatus;
}

// ══════════════════════════════════════════════════════════════════════
// Auditor portal API
// ══════════════════════════════════════════════════════════════════════

export async function createClarification(
  token: string,
  body: ClarificationCreateRequest,
): Promise<ClarificationOut> {
  return api<ClarificationOut>(`${PUBLIC_BASE}/${token}/clarifications`, {
    json: body,
  });
}

export async function listClarificationsAuditor(
  token: string,
): Promise<ClarificationListResponse> {
  return api<ClarificationListResponse>(
    `${PUBLIC_BASE}/${token}/clarifications`,
  );
}

// ══════════════════════════════════════════════════════════════════════
// Admin API
// ══════════════════════════════════════════════════════════════════════

export async function listClarificationsAdmin(
  projectId: string,
  options?: {
    status?: ClarificationStatus;
    priority?: ClarificationPriority;
  },
): Promise<ClarificationListResponse> {
  const qs = new URLSearchParams();
  if (options?.status) qs.set("status_filter", options.status);
  if (options?.priority) qs.set("priority_filter", options.priority);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<ClarificationListResponse>(
    `${ADMIN_BASE}/${projectId}/audit/clarifications${suffix}`,
  );
}

export async function patchClarificationAdmin(
  projectId: string,
  clarificationId: string,
  body: AdminClarificationPatchRequest,
): Promise<ClarificationOut> {
  return api<ClarificationOut>(
    `${ADMIN_BASE}/${projectId}/audit/clarifications/${clarificationId}`,
    { method: "PATCH", json: body },
  );
}

// ══════════════════════════════════════════════════════════════════════
// UI helpers
// ══════════════════════════════════════════════════════════════════════

export const PRIORITY_LABEL: Record<ClarificationPriority, string> = {
  low: "Baja",
  normal: "Normal",
  high: "Alta",
  urgent: "Urgente",
};

export const PRIORITY_VARIANT: Record<
  ClarificationPriority,
  "outline" | "secondary" | "warning" | "danger"
> = {
  low: "outline",
  normal: "secondary",
  high: "warning",
  urgent: "danger",
};

export const STATUS_LABEL: Record<ClarificationStatus, string> = {
  open: "Abierta",
  in_progress: "En revisión",
  responded: "Respondida",
  closed: "Cerrada",
};

export const STATUS_VARIANT: Record<
  ClarificationStatus,
  "outline" | "info" | "success" | "secondary"
> = {
  open: "outline",
  in_progress: "info",
  responded: "success",
  closed: "secondary",
};

export const TARGET_TYPE_LABEL: Record<ClarificationTargetType, string> = {
  general: "Consulta general",
  evidence: "Evidencia",
  medida: "Medida DdA",
  magerit_asset: "Activo MAGERIT",
  magerit_threat: "Amenaza MAGERIT",
  magerit_safeguard: "Salvaguarda MAGERIT",
  plan_task: "Tarea del plan",
  audit_log_entry: "Entrada del registro",
};
