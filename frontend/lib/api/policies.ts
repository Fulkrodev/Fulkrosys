/**
 * Motor 6 — Policies portal cliente API · SAN-E v3.MB-6 atom 1.
 *
 * CCN-STIC 805 cliente review individual 25 policies + firma bulk única.
 *
 * Endpoints:
 *  - GET    /portal/policies/projects/{id}                  · summary tier
 *  - GET    /portal/policies/projects/{id}/list             · 25 cards review state
 *  - POST   /portal/policies/documents/{id}/review          · cliente review action
 *  - GET    /portal/policies/projects/{id}/document-hash    · SHA256 bulk pre-firma
 *  - POST   /portal/policies/projects/{id}/finalize-signoff · link post-firma
 */
import { clientApi } from "@/lib/client-portal-api";

export type PolicyTier = "BASICA" | "MEDIA" | "ALTA";

export type PolicyReviewStatus =
  | "pendiente_revision"
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export type PolicyReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export type PolicyFamily =
  | "fundamental"
  | "identidad"
  | "personal"
  | "informacion"
  | "continuidad"
  | "criptografia"
  | "operacion"
  | "movilidad"
  | "proveedores"
  | "desarrollo"
  | "redes"
  | "fisica"
  | "otros";

export interface PolicyClientView {
  document_id: string | null;
  template_codigo: string;
  nombre: string | null;
  level: 1 | 2;
  family: PolicyFamily;
  docx_path: string | null;
  estado: string | null;
  client_review_status: PolicyReviewStatus | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
  client_signing_intent_id: string | null;
}

export interface PolicySummary {
  project_id: string;
  tier: PolicyTier;
  expected_count: number;
  generated_count: number;
  pending_review_count: number;
  revisada_ok_count: number;
  with_questions_count: number;
  suggest_change_count: number;
  ready_for_bulk_sign: boolean;
  bulk_signing_intent_id: string | null;
  bulk_signed: boolean;
}

export interface PolicyBulkHash {
  project_id: string;
  tier: PolicyTier;
  expected_count: number;
  canonical_length: number;
  document_hash_sha256: string;
  ready_for_signing: boolean;
}

export interface PolicyFinalizeSignoffResponse {
  project_id: string;
  signing_intent_id: string;
  documents_linked: number;
}

export async function getPoliciesSummary(
  projectId: string,
): Promise<PolicySummary> {
  return clientApi<PolicySummary>(`/portal/policies/projects/${projectId}`);
}

export async function listClientPolicies(
  projectId: string,
): Promise<PolicyClientView[]> {
  return clientApi<PolicyClientView[]>(
    `/portal/policies/projects/${projectId}/list`,
  );
}

export async function reviewClientPolicy(
  documentId: string,
  action: PolicyReviewAction,
  note?: string,
): Promise<PolicyClientView> {
  return clientApi<PolicyClientView>(
    `/portal/policies/documents/${documentId}/review`,
    { json: { action, note: note ?? null } },
  );
}

export async function getPoliciesBulkHash(
  projectId: string,
): Promise<PolicyBulkHash> {
  return clientApi<PolicyBulkHash>(
    `/portal/policies/projects/${projectId}/document-hash`,
  );
}

export async function finalizePoliciesSignoff(
  projectId: string,
  signingIntentId: string,
): Promise<PolicyFinalizeSignoffResponse> {
  return clientApi<PolicyFinalizeSignoffResponse>(
    `/portal/policies/projects/${projectId}/finalize-signoff`,
    { json: { signing_intent_id: signingIntentId } },
  );
}
