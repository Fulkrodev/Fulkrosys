/**
 * Clientes API para los 3 portales publicos (Motor 8 v5.1 — 3B).
 */
import { api } from "@/lib/api";
import type {
  PentesterCompleteResponse,
  PentesterFindingInput,
  PentesterPortalData,
  RemediationData,
  RemediationGuide,
  RemediationRetestResult,
  VerifyAuthData,
  VerifyAuthSignResponse,
} from "@/lib/public-portals-types";

const BASE = "/api/v1/public";

// ─── Remediation portal ───────────────────────────────────────────────

export async function getRemediationData(
  token: string,
): Promise<RemediationData> {
  return api<RemediationData>(`${BASE}/remediation/${token}`);
}

export async function getRemediationGuide(
  token: string,
  findingId: string,
): Promise<RemediationGuide> {
  return api<RemediationGuide>(
    `${BASE}/remediation/${token}/findings/${findingId}/guide`,
  );
}

export async function markRemediationFixed(
  token: string,
  findingId: string,
): Promise<RemediationRetestResult> {
  return api<RemediationRetestResult>(
    `${BASE}/remediation/${token}/findings/${findingId}/fixed`,
    { json: {} },
  );
}

// ─── Pentester portal ─────────────────────────────────────────────────

export async function getPentesterData(
  token: string,
): Promise<PentesterPortalData> {
  return api<PentesterPortalData>(`${BASE}/pentester-portal/${token}`);
}

export function pentesterDocumentUrl(token: string, index: number): string {
  return `${BASE}/pentester-portal/${token}/documents/${index}`;
}

export function pentesterVpnUrl(token: string): string {
  return `${BASE}/pentester-portal/${token}/vpn-config`;
}

export async function submitPentesterFindings(
  token: string,
  findings: PentesterFindingInput[],
): Promise<{ submitted: number; total_in_handoff: number }> {
  return api(`${BASE}/pentester-portal/${token}/findings`, {
    json: { findings },
  });
}

export async function uploadPentesterPdf(
  token: string,
  file: File,
): Promise<{
  status: string;
  filename: string;
  size_bytes: number;
  hash_sha256: string;
  auto_parsed_findings: number;
}> {
  const form = new FormData();
  form.append("file", file);
  // Use fetch directly to send multipart
  const response = await fetch(
    `${BASE}/pentester-portal/${token}/upload-pdf`,
    {
      method: "POST",
      body: form,
      credentials: "include",
    },
  );
  if (!response.ok) {
    throw new Error(
      `Upload failed: ${response.status} ${response.statusText}`,
    );
  }
  return response.json();
}

export async function completePentesterEngagement(
  token: string,
): Promise<PentesterCompleteResponse> {
  return api<PentesterCompleteResponse>(
    `${BASE}/pentester-portal/${token}/complete`,
    { json: {} },
  );
}

// ─── Download portal (M25 public_api) ────────────────────────────────

export interface DownloadMetadata {
  purpose: string;
  filename: string;
  size_bytes: number | null;
  content_type: string;
  sha256?: string;
  ed25519_signature?: string;
  expires_at: string | null;
  download_url: string;
}

export async function getDownloadMetadata(
  token: string,
): Promise<DownloadMetadata> {
  return api<DownloadMetadata>(`${BASE}/download/${token}`);
}

export function downloadFileUrl(token: string): string {
  return `${BASE}/download/${token}/file`;
}

// ─── Retainer offer (M25 public_api · oferta + reconsideracion) ───────

export interface RetainerOfferMetadata {
  purpose: "oferta_retainer" | "reconsideracion_retainer";
  is_reconsideration: boolean;
  project_name: string | null;
  recommended_tiers: string[];
  previous_decline_reason: string | null;
}

export interface RetainerOfferRespondBody {
  decision: "accept" | "decline" | "thinking";
  tier?: string | null;
  comentario?: string | null;
}

export interface RetainerOfferRespondResponse {
  status: string;
  decision: string;
  tier: string | null;
  precio_mensual: number;
  result: Record<string, unknown>;
}

export async function getRetainerOffer(
  token: string,
): Promise<RetainerOfferMetadata> {
  return api<RetainerOfferMetadata>(`${BASE}/retainer-offer/${token}`);
}

export async function respondRetainerOffer(
  token: string,
  body: RetainerOfferRespondBody,
): Promise<RetainerOfferRespondResponse> {
  return api<RetainerOfferRespondResponse>(
    `${BASE}/retainer-offer/${token}/respond`,
    { json: body },
  );
}

// ─── Verify-auth portal ───────────────────────────────────────────────

export async function getVerifyAuthData(
  token: string,
): Promise<VerifyAuthData> {
  return api<VerifyAuthData>(`${BASE}/verify-auth/${token}`);
}

export async function requestVerifyAuthOtp(
  token: string,
): Promise<{ delivery_method: string; expires_in_seconds: number }> {
  return api(`${BASE}/verify-auth/${token}/request-otp`, {
    json: { delivery_method: "email" },
  });
}

export async function submitVerifyAuth(
  token: string,
  body: { accepted_legal: boolean; otp?: string },
): Promise<VerifyAuthSignResponse> {
  return api<VerifyAuthSignResponse>(
    `${BASE}/verify-auth/${token}/submit`,
    { json: body },
  );
}
