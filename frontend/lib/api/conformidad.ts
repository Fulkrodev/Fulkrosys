/**
 * Motor 27 — Conformidad cliente in-portal API · SAN-E v3.MB-5.6.
 *
 * 5 endpoints bajo /api/v1/portal/conformidad cliente-facing UX.
 * Backend file path es backend/app/motors/m27_conformity/portal_api.py.
 *
 * Escenario X audit-driven: BasicDeclarationRow tier-aware
 * - BASICA → declaration_type='initial' (E-041 self-declaration)
 * - MEDIA/ALTA → declaration_type='commitment_pre_certification' (pre-auditor ENAC)
 */
import { clientApi } from "@/lib/client-portal-api";


export type DeclarationType =
  | "initial"
  | "commitment_pre_certification"
  | "renewal";


export type ProjectTier = "BASICA" | "MEDIA" | "ALTA";


export interface ConformidadDeclarationClientView {
  id: string;
  project_id: string;
  declaration_type: DeclarationType;
  tier: ProjectTier;
  workflow_label: string;
  next_step_post_signature: string;
  /** #2 Ola 7 · explica en llano que firma la Dirección · solo BÁSICA · null en MEDIA/ALTA. */
  signer_explanation?: string | null;

  responsible_person_name: string | null;
  responsible_person_email: string | null;
  status: string;
  signed_at: string | null;
  signed_hash: string | null;

  client_reviewed_at: string | null;
  client_reviewed_by_user_id: string | null;
  client_concerns_note: string | null;
  client_signing_intent_id: string | null;

  readiness_snapshot_jsonb: Record<string, unknown> | null;
  last_modified_at: string | null;
}


export interface ReadinessItem {
  label: string;
  ready: boolean;
  detail: string | null;
}


export interface ConformityReadinessView {
  tier: ProjectTier;
  ready_for_conformity_sign: boolean;
  blockers: string[];
  captured_at: string;
  items: ReadinessItem[];
  dda_signed_at: string | null;
  magerit_signed_at: string | null;
  pentest_signed_at: string | null;
  evidence_count: number;
  policies_signed_count: number;
}


export interface ConformidadDocumentHashResponse {
  document_hash_sha256: string;
  canonical_length: number;
  declaration_id: string;
  last_modified_at: string | null;
  ready_for_signing: boolean;
}


export interface PostSignatureBasicaResponse {
  declaration_type: "initial";
  distintivo_svg_url: string;
  cert_id_url: string;
  declaration_docx_url: string;
  summary: string;
}


export interface PostSignatureCommitmentResponse {
  declaration_type: "commitment_pre_certification";
  commitment_signed_at: string;
  next_step_summary: string;
  next_step_eta_days_min: number;
  next_step_eta_days_max: number;
  contacto_marcos_email: string;
}


export type PostSignatureResponse =
  | PostSignatureBasicaResponse
  | PostSignatureCommitmentResponse;


/** GET /api/v1/portal/conformidad/projects/{id}/declaration */
export async function getConformidadDeclaration(
  projectId: string,
): Promise<ConformidadDeclarationClientView> {
  return clientApi<ConformidadDeclarationClientView>(
    `/portal/conformidad/projects/${projectId}/declaration`,
  );
}


/** GET /api/v1/portal/conformidad/projects/{id}/readiness */
export async function getConformidadReadiness(
  projectId: string,
): Promise<ConformityReadinessView> {
  return clientApi<ConformityReadinessView>(
    `/portal/conformidad/projects/${projectId}/readiness`,
  );
}


/** POST /api/v1/portal/conformidad/projects/{id}/mark-reviewed */
export async function markConformidadReviewed(
  projectId: string,
  concernsNote?: string,
): Promise<ConformidadDeclarationClientView> {
  return clientApi<ConformidadDeclarationClientView>(
    `/portal/conformidad/projects/${projectId}/mark-reviewed`,
    {
      method: "POST",
      json: { concerns_note: concernsNote ?? null },
    },
  );
}


/** GET /api/v1/portal/conformidad/projects/{id}/document-hash */
export async function getConformidadDocumentHash(
  projectId: string,
): Promise<ConformidadDocumentHashResponse> {
  return clientApi<ConformidadDocumentHashResponse>(
    `/portal/conformidad/projects/${projectId}/document-hash`,
  );
}


/** GET /api/v1/portal/conformidad/projects/{id}/post-signature */
export async function getConformidadPostSignature(
  projectId: string,
): Promise<PostSignatureResponse> {
  return clientApi<PostSignatureResponse>(
    `/portal/conformidad/projects/${projectId}/post-signature`,
  );
}
