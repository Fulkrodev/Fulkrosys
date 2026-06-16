/**
 * In-portal signing service · API wrapper · SAN-E v3.MB-5.3.C.
 *
 * Reusable across signable_types: dda · magerit_validation ·
 * pentest_authorization · conformidad_ens · acta_comite · retainer_offer ·
 * policy_approval · incident_close · dpc_anual · renewal · document_generic.
 *
 * Auth: cookie session ClientUser + CSRF triple binding (clientApi wrapper).
 *
 * Backend M05 signing service · ADR-020 v5 IMPLEMENTED FULLY:
 * - Ed25519 process-level signature
 * - Hash chain audit per project
 * - Step-up OTP via email (5 docs críticos · TTL 5min · 5 attempts max)
 * - signing_intents + signing_events INMUTABLE log
 */
import { clientApi } from "@/lib/client-portal-api";

// SignableType canónico (18 tipos · espejo backend) vive en un único módulo.
// Re-exportado aquí para no romper los importadores existentes (§4.1 line 341).
export type { SignableType } from "@/lib/api/signable-types";
import type { SignableType } from "@/lib/api/signable-types";

export type SigningIntentStatus =
  | "pending"
  | "otp_required"
  | "otp_verified"
  | "signed"
  | "rejected"
  | "expired";

export interface SigningIntent {
  id: string;
  project_id: string;
  signable_type: SignableType;
  status: SigningIntentStatus;
  requires_step_up_otp: boolean;
  document_hash_sha256: string;
  expires_at: string;
  created_by_user_id: string;
  created_at: string;
}

export interface CreateSigningIntentRequest {
  project_id: string;
  signable_type: SignableType;
  document_hash_sha256: string;
  document_id?: string;
  signable_ref_id?: string;
  signable_ref_type?: string;
  intent_payload?: Record<string, unknown>;
}

export interface RequestOtpResponse {
  otp_sent: boolean;
  sent_to_email_masked: string;
  expires_in_seconds: number;
  expires_at: string;
}

export interface SignedDocumentResponse {
  intent_id: string;
  signature_event_id: string;
  signed_at: string;
  event_hash_sha256: string;
}

export async function createSigningIntent(
  req: CreateSigningIntentRequest,
): Promise<SigningIntent> {
  return clientApi<SigningIntent>(`/portal/signing/intents`, {
    method: "POST",
    json: req,
  });
}

export async function requestStepUpOtp(
  intentId: string,
): Promise<RequestOtpResponse> {
  return clientApi<RequestOtpResponse>(
    `/portal/signing/intents/${intentId}/request-otp`,
    { method: "POST", json: {} },
  );
}

export async function verifyStepUpOtp(
  intentId: string,
  otpCode: string,
): Promise<{ otp_verified: boolean }> {
  return clientApi<{ otp_verified: boolean }>(
    `/portal/signing/intents/${intentId}/verify-otp`,
    { method: "POST", json: { otp_code: otpCode } },
  );
}

export async function signIntent(
  intentId: string,
): Promise<SignedDocumentResponse> {
  return clientApi<SignedDocumentResponse>(
    `/portal/signing/intents/${intentId}/sign`,
    { method: "POST", json: {} },
  );
}

export async function rejectIntent(
  intentId: string,
  reason: string,
): Promise<{ rejected: boolean }> {
  return clientApi<{ rejected: boolean }>(
    `/portal/signing/intents/${intentId}/reject`,
    { method: "POST", json: { reason } },
  );
}

// ════════════════════════════════════════════════════════════════════
// Ejecutable 7.7 · TIER 1 canvas signing endpoints
// ════════════════════════════════════════════════════════════════════

export interface SignCanvasRequest {
  signature_canvas_dataurl: string;
  signed_name: string;
  signed_surname: string;
}

export async function signIntentCanvas(
  intentId: string,
  req: SignCanvasRequest,
): Promise<SignedDocumentResponse> {
  return clientApi<SignedDocumentResponse>(
    `/portal/signing/intents/${intentId}/sign-canvas`,
    { method: "POST", json: req },
  );
}

export interface PendingSignatureCard {
  intent_id: string;
  signable_type: SignableType;
  signable_label: string;
  document_id: string | null;
  document_hash_sha256: string;
  requires_step_up_otp: boolean;
  expires_at: string;
  created_at: string;
  portal_path: string;
}

export interface PendingSignaturesResponse {
  cliente_user_id: string;
  total_pending: number;
  pending: PendingSignatureCard[];
}

export async function listPendingSignatures(
  projectId: string,
): Promise<PendingSignaturesResponse> {
  return clientApi<PendingSignaturesResponse>(
    `/portal/signing/projects/${projectId}/pending`,
  );
}

// ════════════════════════════════════════════════════════════════════
// Helper específico DdA · document hash determinista pre-firma
// ════════════════════════════════════════════════════════════════════

export interface DdaDocumentHashResponse {
  project_id: string;
  document_hash_sha256: string;
  canonical_length: number;
  measures_count: number;
  last_modified_at: string | null;
  ready_for_signing: boolean;
}

export async function getDdaDocumentHash(
  projectId: string,
): Promise<DdaDocumentHashResponse> {
  return clientApi<DdaDocumentHashResponse>(
    `/portal/dda/projects/${projectId}/document-hash`,
  );
}
