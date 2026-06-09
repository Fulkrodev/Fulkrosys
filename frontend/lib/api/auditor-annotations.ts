/**
 * Auditor portal annotations API client · CLUSTER 3 Phase C1.3.
 *
 * Wraps backend `/api/v1/public/auditor-portal/{token}/annotations/*` (auditor)
 * + `/api/v1/admin/projects/{project_id}/audit/annotations/*` (admin).
 *
 * Annotations cross-motor inspection · 7 target types · 4 severity levels ·
 * 4 status workflow values. RLS isolation enforced backend (Sub-atom 5.A pattern).
 */
import { api } from "@/lib/api";

const PUBLIC_BASE = "/api/v1/public/auditor-portal";
const ADMIN_BASE = "/api/v1/admin/projects";

export type AnnotationTargetType =
  | "evidence"
  | "medida"
  | "magerit_asset"
  | "magerit_threat"
  | "magerit_safeguard"
  | "plan_task"
  | "audit_log_entry";

export type AnnotationSeverity = "info" | "warning" | "concern" | "critical";

export type AnnotationStatus =
  | "open"
  | "admin_reviewed"
  | "resolved"
  | "dismissed";

export interface AnnotationOut {
  id: string;
  project_id: string;
  target_type: AnnotationTargetType;
  target_id: string;
  annotation_text: string;
  flag_severity: AnnotationSeverity;
  status: AnnotationStatus;
  admin_response: string | null;
  admin_responded_at: string | null;
  admin_responded_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AnnotationListResponse {
  total: number;
  items: AnnotationOut[];
}

export interface AnnotationCreateRequest {
  target_type: AnnotationTargetType;
  target_id: string;
  annotation_text: string;
  flag_severity: AnnotationSeverity;
}

export interface AdminAnnotationPatchRequest {
  admin_response?: string;
  status?: AnnotationStatus;
}

// ══════════════════════════════════════════════════════════════════════
// Auditor portal API (token-bounded)
// ══════════════════════════════════════════════════════════════════════

export async function createAnnotation(
  token: string,
  body: AnnotationCreateRequest,
): Promise<AnnotationOut> {
  return api<AnnotationOut>(`${PUBLIC_BASE}/${token}/annotations`, {
    json: body,
  });
}

export async function listAnnotationsAuditor(
  token: string,
): Promise<AnnotationListResponse> {
  return api<AnnotationListResponse>(`${PUBLIC_BASE}/${token}/annotations`);
}

export async function getAnnotationAuditor(
  token: string,
  annotationId: string,
): Promise<AnnotationOut> {
  return api<AnnotationOut>(
    `${PUBLIC_BASE}/${token}/annotations/${annotationId}`,
  );
}

export async function deleteAnnotationAuditor(
  token: string,
  annotationId: string,
): Promise<void> {
  return api<void>(
    `${PUBLIC_BASE}/${token}/annotations/${annotationId}`,
    { method: "DELETE" },
  );
}

// ══════════════════════════════════════════════════════════════════════
// Admin API (require_owner)
// ══════════════════════════════════════════════════════════════════════

export async function listAnnotationsAdmin(
  projectId: string,
  options?: { status?: AnnotationStatus },
): Promise<AnnotationListResponse> {
  const qs = options?.status ? `?status_filter=${options.status}` : "";
  return api<AnnotationListResponse>(
    `${ADMIN_BASE}/${projectId}/audit/annotations${qs}`,
  );
}

export async function patchAnnotationAdmin(
  projectId: string,
  annotationId: string,
  body: AdminAnnotationPatchRequest,
): Promise<AnnotationOut> {
  return api<AnnotationOut>(
    `${ADMIN_BASE}/${projectId}/audit/annotations/${annotationId}`,
    { method: "PATCH", json: body },
  );
}

// ══════════════════════════════════════════════════════════════════════
// UI helpers
// ══════════════════════════════════════════════════════════════════════

export const SEVERITY_LABEL: Record<AnnotationSeverity, string> = {
  info: "Informativo",
  warning: "Atención",
  concern: "Preocupación",
  critical: "Crítico",
};

export const SEVERITY_VARIANT: Record<
  AnnotationSeverity,
  "outline" | "secondary" | "warning" | "danger"
> = {
  info: "outline",
  warning: "secondary",
  concern: "warning",
  critical: "danger",
};

export const STATUS_LABEL: Record<AnnotationStatus, string> = {
  open: "Abierta",
  admin_reviewed: "Revisada por admin",
  resolved: "Resuelta",
  dismissed: "Descartada",
};

export const STATUS_VARIANT: Record<
  AnnotationStatus,
  "outline" | "info" | "success" | "secondary"
> = {
  open: "outline",
  admin_reviewed: "info",
  resolved: "success",
  dismissed: "secondary",
};

export const TARGET_TYPE_LABEL: Record<AnnotationTargetType, string> = {
  evidence: "Evidencia",
  medida: "Medida DdA",
  magerit_asset: "Activo MAGERIT",
  magerit_threat: "Amenaza MAGERIT",
  magerit_safeguard: "Salvaguarda MAGERIT",
  plan_task: "Tarea del plan",
  audit_log_entry: "Entrada del registro",
};
