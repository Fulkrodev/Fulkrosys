/**
 * Motor 27 — DPC anual portal cliente API · SAN-E v3.MB-6 atom 2.
 *
 * Declaración Protección Continuidad (DPC) anual · art.25 RD 311/2022 · CCN-STIC 806.
 *
 * Endpoints:
 *  - GET    /portal/dpc-anual/projects/{id}                        · list current + history
 *  - GET    /portal/dpc-anual/declarations/{id}                    · detail + 4 secciones
 *  - POST   /portal/dpc-anual/declarations/{id}/review             · cliente review action
 *  - GET    /portal/dpc-anual/declarations/{id}/document-hash      · SHA256 pre-firma
 *  - POST   /portal/dpc-anual/declarations/{id}/finalize-signoff   · link signing_intent
 */
import { clientApi } from "@/lib/client-portal-api";

export type DpcStatus = "draft" | "signed" | "expired";

export type DpcReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export interface DpcDeclaration {
  id: string;
  project_id: string;
  anniversary_year: number;
  status: DpcStatus;
  client_concerns_note: string | null;
  client_reviewed_at: string | null;
  client_signing_intent_id: string | null;
  signed_at: string | null;
  conformidad_signature_id: string | null;
  anniversary_date: string;
  days_until_anniversary: number | null;
  created_at: string;
}

export interface DpcContextSections {
  sla_section: Record<string, unknown>;
  recovery_section: Record<string, unknown>;
  incidents_section: Record<string, unknown>;
  roadmap_section: Record<string, unknown>;
}

export interface DpcContextDetail extends DpcContextSections {
  declaration: DpcDeclaration;
}

export interface DpcDocumentHash {
  declaration_id: string;
  anniversary_year: number;
  canonical_length: number;
  document_hash_sha256: string;
  ready_for_signing: boolean;
}

export interface DpcFinalizeSignoffResponse {
  declaration_id: string;
  signing_intent_id: string;
  signed_at: string;
  signed_hash: string;
}

export async function listDpcDeclarations(
  projectId: string,
): Promise<DpcDeclaration[]> {
  return clientApi<DpcDeclaration[]>(`/portal/dpc-anual/projects/${projectId}`);
}

export async function getDpcDeclarationDetail(
  declarationId: string,
): Promise<DpcContextDetail> {
  return clientApi<DpcContextDetail>(
    `/portal/dpc-anual/declarations/${declarationId}`,
  );
}

export async function reviewDpcDeclaration(
  declarationId: string,
  action: DpcReviewAction,
  note?: string,
): Promise<DpcDeclaration> {
  return clientApi<DpcDeclaration>(
    `/portal/dpc-anual/declarations/${declarationId}/review`,
    { json: { action, note: note ?? null } },
  );
}

export async function getDpcDocumentHash(
  declarationId: string,
): Promise<DpcDocumentHash> {
  return clientApi<DpcDocumentHash>(
    `/portal/dpc-anual/declarations/${declarationId}/document-hash`,
  );
}

export async function finalizeDpcSignoff(
  declarationId: string,
  signingIntentId: string,
): Promise<DpcFinalizeSignoffResponse> {
  return clientApi<DpcFinalizeSignoffResponse>(
    `/portal/dpc-anual/declarations/${declarationId}/finalize-signoff`,
    { json: { signing_intent_id: signingIntentId } },
  );
}
