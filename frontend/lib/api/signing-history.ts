/**
 * Motor 05 — Signing history (cliente firmas hub) · SAN-E v3.MB-6 atom 0.2.
 *
 * GET /api/v1/portal/signing/projects/{project_id}/history
 *
 * Cliente VE TODAS las firmas previas + chain integrity status.
 * Cards per signable_type operativo (DdA · MAGERIT · Pentest · Conformidad).
 * Cards 'pending_creation' linkean al portal correspondiente para iniciar flow.
 */
import { clientApi } from "@/lib/client-portal-api";

export type SignableType =
  | "dda"
  | "magerit_validation"
  | "policy_approval"
  | "pentest_authorization"
  | "conformidad_ens"
  | "dpc_anual"
  | "retainer_quarterly_signoff";

export type SignatureCardStatus =
  | "pending_creation"
  | "pending"
  | "otp_required"
  | "otp_verified"
  | "signed"
  | "rejected"
  | "expired";

export interface SignatureCardView {
  signable_type: SignableType;
  signable_label: string;
  intent_id: string | null;
  status: SignatureCardStatus;
  signed_at: string | null;
  signature_event_id: string | null;
  document_hash_sha256: string | null;
  event_hash_sha256: string | null;
  chain_position: number | null;
  portal_path: string;
}

export interface SigningHistoryClientResponse {
  project_id: string;
  signatures: SignatureCardView[];
  chain_valid: boolean;
  broken_links_count: number;
  total_signed: number;
  total_expected: number;
  readiness_snapshot: Record<string, unknown> | null;
}

export async function getClientSigningHistory(
  projectId: string,
): Promise<SigningHistoryClientResponse> {
  return clientApi<SigningHistoryClientResponse>(
    `/portal/signing/projects/${projectId}/history`,
  );
}
