/**
 * Motor 19 — Incidents portal cliente API · SAN-E v3.MB-6 atom 3.
 *
 * CCN-STIC 817 cliente review + close signoff workflow.
 * Cliente VE solo workflow_state IN (resolved · closed).
 *
 * Endpoints:
 *  - GET    /portal/incidents/projects/{id}                 · list visible
 *  - GET    /portal/incidents/{id}                          · detail single
 *  - POST   /portal/incidents/{id}/review                   · review action
 *  - GET    /portal/incidents/{id}/document-hash            · SHA256 pre-firma
 *  - POST   /portal/incidents/{id}/finalize-close           · link signing_intent
 */
import { clientApi } from "@/lib/client-portal-api";

export type IncidentSeverity = "critical" | "high" | "medium" | "low";

export type IncidentWorkflowState =
  | "created"
  | "triaged"
  | "investigated"
  | "mitigated"
  | "resolved"
  | "closed";

export type IncidentReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export interface CcnCertRouting {
  route_type: "internal_only" | "lucia_federation" | "manual_notification";
  deadline_hours: number | null;
  action_required: string;
  reasoning: string;
}

export interface IncidentClient {
  id: string;
  project_id: string;
  fecha: string | null;
  severidad: IncidentSeverity | null;
  descripcion: string | null;
  resolucion: string | null;
  workflow_state: IncidentWorkflowState | null;
  client_review_status: string | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
  client_signing_intent_id: string | null;
  ccn_cert_routing: CcnCertRouting | null;
  reported_to_ccn_cert_at: string | null;
  manual_notification_doc_id: string | null;
  lucia_submission_id: string | null;
  notificado_lucia: boolean | null;
  created_at: string;
}

export interface IncidentDocumentHash {
  incident_id: string;
  workflow_state: string;
  canonical_length: number;
  document_hash_sha256: string;
  ready_for_signing: boolean;
}

export interface IncidentFinalizeCloseResponse {
  incident_id: string;
  signing_intent_id: string;
  workflow_state: string;
}

export async function listClientIncidents(
  projectId: string,
): Promise<IncidentClient[]> {
  return clientApi<IncidentClient[]>(`/portal/incidents/projects/${projectId}`);
}

export async function getIncidentDetail(
  incidentId: string,
): Promise<IncidentClient> {
  return clientApi<IncidentClient>(`/portal/incidents/${incidentId}`);
}

export async function reviewIncident(
  incidentId: string,
  action: IncidentReviewAction,
  note?: string,
): Promise<IncidentClient> {
  return clientApi<IncidentClient>(
    `/portal/incidents/${incidentId}/review`,
    { json: { action, note: note ?? null } },
  );
}

export async function getIncidentCloseHash(
  incidentId: string,
): Promise<IncidentDocumentHash> {
  return clientApi<IncidentDocumentHash>(
    `/portal/incidents/${incidentId}/document-hash`,
  );
}

export async function finalizeIncidentClose(
  incidentId: string,
  signingIntentId: string,
): Promise<IncidentFinalizeCloseResponse> {
  return clientApi<IncidentFinalizeCloseResponse>(
    `/portal/incidents/${incidentId}/finalize-close`,
    { json: { signing_intent_id: signingIntentId } },
  );
}
