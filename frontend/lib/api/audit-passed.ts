/**
 * API client · admin mark-audit-passed endpoint.
 *
 * Sesión 3B-2B.6 Cluster 1 Phase 2 · Marcos marca resultado auditoría ENAC.
 * Backend POST /api/v1/projects/{id}/audit/mark-passed (m25_lifecycle).
 */
import { api } from "@/lib/api";

export type AuditResult = "passed" | "observed" | "correction_required" | "failed";

export interface MarkAuditPassedRequest {
  result: AuditResult;
  audit_report_ref?: string | null;
  cascade_certify?: boolean;
  performed_by?: string;
}

export interface MarkAuditPassedResponse {
  event_id: string;
  event_type: string;
  result: AuditResult;
  audit_passed_at: string;
  audit_report_ref: string | null;
  lifecycle_state: string;
  certified_event_id?: string;
  certified_skipped_reason?: string;
}

export async function markAuditPassed(
  projectId: string,
  body: MarkAuditPassedRequest,
): Promise<MarkAuditPassedResponse> {
  return api<MarkAuditPassedResponse>(
    `/api/v1/projects/${projectId}/audit/mark-passed`,
    { method: "POST", json: body },
  );
}
