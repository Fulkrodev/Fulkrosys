/**
 * Motor 23 — Retainer quarterly checkin portal cliente · MB-6 atom 4.
 *
 * Separated from `retainer.ts` existing (admin TanStack RQ pattern) ·
 * cliente checkin usa useState pattern (Consideration A).
 *
 * Endpoints:
 *  - GET    /portal/retainer-checkin/projects/{id}          · list visible
 *  - GET    /portal/retainer-checkin/{id}                   · detail single
 *  - POST   /portal/retainer-checkin/{id}/review            · review action
 *  - GET    /portal/retainer-checkin/{id}/document-hash     · SHA256 pre-firma
 *  - POST   /portal/retainer-checkin/{id}/finalize-signoff  · link signing_intent
 */
import { clientApi } from "@/lib/client-portal-api";

export type CheckinReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export type RagStatus = "green" | "amber" | "red";

export interface CheckinSummaryJsonb {
  schema_version: string;
  actividades: {
    completed: number;
    pending: number;
    overdue: number;
    total: number;
  };
  incidents: {
    detected: number;
    resolved: number;
    ccn_cert_routed: number;
  };
  vulnerabilidades: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    mitigated: number;
  };
  normativa_changes: {
    relevant_count: number;
    summary: string;
  };
  rag_overall: RagStatus;
  stakeholder_changes: {
    count: number;
    summary: string;
  };
  evidence_freshness: {
    fresh: number;
    stale: number;
  };
  captured_at: string;
}

export interface RetainerCheckin {
  id: string;
  project_id: string;
  period_quarter: string | null;
  period_start: string;
  period_end: string;
  activities_completed: number;
  activities_pending: number;
  activities_overdue: number;
  incidents_detected: number;
  normativa_changes_relevant: number;
  vulns_critical: number;
  rag_overall: RagStatus | null;
  admin_curation_status: string;
  sent_at: string | null;
  client_review_status: string | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
  client_signing_intent_id: string | null;
  summary_jsonb: CheckinSummaryJsonb | null;
  schema_version: string;
  created_at: string;
}

export interface CheckinDocumentHash {
  report_id: string;
  period_quarter: string | null;
  canonical_length: number;
  document_hash_sha256: string;
  ready_for_signing: boolean;
}

export interface CheckinFinalizeSignoffResponse {
  report_id: string;
  signing_intent_id: string;
}

export async function listClientCheckins(
  projectId: string,
): Promise<RetainerCheckin[]> {
  return clientApi<RetainerCheckin[]>(
    `/portal/retainer-checkin/projects/${projectId}`,
  );
}

export async function getCheckinDetail(
  reportId: string,
): Promise<RetainerCheckin> {
  return clientApi<RetainerCheckin>(`/portal/retainer-checkin/${reportId}`);
}

export async function reviewCheckin(
  reportId: string,
  action: CheckinReviewAction,
  note?: string,
): Promise<RetainerCheckin> {
  return clientApi<RetainerCheckin>(
    `/portal/retainer-checkin/${reportId}/review`,
    { json: { action, note: note ?? null } },
  );
}

export async function getCheckinDocumentHash(
  reportId: string,
): Promise<CheckinDocumentHash> {
  return clientApi<CheckinDocumentHash>(
    `/portal/retainer-checkin/${reportId}/document-hash`,
  );
}

export async function finalizeCheckinSignoff(
  reportId: string,
  signingIntentId: string,
): Promise<CheckinFinalizeSignoffResponse> {
  return clientApi<CheckinFinalizeSignoffResponse>(
    `/portal/retainer-checkin/${reportId}/finalize-signoff`,
    { json: { signing_intent_id: signingIntentId } },
  );
}
