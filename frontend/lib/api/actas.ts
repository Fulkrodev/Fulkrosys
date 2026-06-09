/**
 * Motor m_meetings · Actas portal cliente · SAN-E v3.MB-6 atom 5.
 *
 * 4 tipos signable cliente · reuse acta_comite signable_type + acta_subtype col.
 * NO step-up OTP (acta_comite NOT in REQUIRES_STEP_UP_OTP frozenset).
 *
 * Endpoints:
 *  - GET   /portal/actas/projects/{id}                · list + optional subtype filter
 *  - GET   /portal/actas/{id}                         · detail
 *  - POST  /portal/actas/{id}/review                  · cliente review MixinA
 *  - GET   /portal/actas/{id}/document-hash           · SHA256 pre-firma
 *  - POST  /portal/actas/{id}/finalize-signoff        · link signing_intent
 */
import { clientApi } from "@/lib/client-portal-api";

export type ActaSubtype =
  | "kickoff"
  | "checkpoint"
  | "audit"
  | "cierre"
  | "other";

export const ACTA_SUBTYPES: ActaSubtype[] = [
  "kickoff",
  "checkpoint",
  "audit",
  "cierre",
  "other",
];

export const ACTA_SUBTYPE_LABELS: Record<ActaSubtype, string> = {
  kickoff: "Acta Inicio Proyecto",
  checkpoint: "Acta Revisión Periódica",
  audit: "Acta Auditoría ENAC",
  cierre: "Acta Cierre Proyecto",
  other: "Otra Acta",
};

export const ACTA_SUBTYPE_SHORT_LABELS: Record<ActaSubtype, string> = {
  kickoff: "Kickoff",
  checkpoint: "Checkpoint",
  audit: "Audit",
  cierre: "Cierre",
  other: "Otra",
};

export type ActaReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export interface ActaAsistente {
  nombre?: string;
  cargo?: string;
  organizacion?: string;
  email?: string;
}

export interface ActaOrdenItem {
  punto?: string;
  titulo?: string;
  ponente?: string;
  tiempo_min?: number;
}

export interface ActaAcuerdoItem {
  numero?: string | number;
  descripcion?: string;
  owner?: string;
  fecha_limite?: string;
}

export interface ActaProximoPasoItem {
  descripcion?: string;
  owner?: string;
  fecha_limite?: string;
}

export interface ActaFirmaEntry {
  actor?: string;
  asistente_idx?: number;
  asistente_nombre?: string;
  magic_link_id?: string;
  signing_intent_id?: string;
  firmado_at?: string;
  ip?: string | null;
  action_proof?: string | null;
}

export interface ActaClientView {
  id: string;
  project_id: string;
  codigo: string | null;
  acta_subtype: ActaSubtype | null;
  acta_subtype_label: string;
  titulo: string | null;
  fecha: string | null;
  lugar: string | null;
  presidente: string | null;
  secretario: string | null;
  asistentes: ActaAsistente[] | null;
  orden_del_dia: ActaOrdenItem[] | null;
  acuerdos_jsonb: ActaAcuerdoItem[] | null;
  proximos_pasos: ActaProximoPasoItem[] | null;
  notas_libres: string | null;
  estado: string | null;
  admin_curation_status: string;
  hash_sha256: string | null;
  signature_ed25519: string | null;
  firmas: ActaFirmaEntry[] | null;
  fully_signed_at: string | null;
  client_review_status: string | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
  client_signing_intent_id: string | null;
  pdf_path: string | null;
  created_at: string;
}

export interface ActaDocumentHash {
  meeting_id: string;
  acta_subtype: ActaSubtype | null;
  canonical_length: number;
  document_hash_sha256: string;
  ready_for_signing: boolean;
}

export interface ActaFinalizeSignoffResponse {
  meeting_id: string;
  signing_intent_id: string;
}

export async function listClientActas(
  projectId: string,
  subtype?: ActaSubtype,
): Promise<ActaClientView[]> {
  const qs = subtype ? `?subtype=${encodeURIComponent(subtype)}` : "";
  return clientApi<ActaClientView[]>(
    `/portal/actas/projects/${projectId}${qs}`,
  );
}

export async function getActaDetail(
  meetingId: string,
): Promise<ActaClientView> {
  return clientApi<ActaClientView>(`/portal/actas/${meetingId}`);
}

export async function reviewActa(
  meetingId: string,
  action: ActaReviewAction,
  note?: string,
): Promise<ActaClientView> {
  return clientApi<ActaClientView>(
    `/portal/actas/${meetingId}/review`,
    { json: { action, note: note ?? null } },
  );
}

export async function getActaDocumentHash(
  meetingId: string,
): Promise<ActaDocumentHash> {
  return clientApi<ActaDocumentHash>(
    `/portal/actas/${meetingId}/document-hash`,
  );
}

export async function finalizeActaSignoff(
  meetingId: string,
  signingIntentId: string,
): Promise<ActaFinalizeSignoffResponse> {
  return clientApi<ActaFinalizeSignoffResponse>(
    `/portal/actas/${meetingId}/finalize-signoff`,
    { json: { signing_intent_id: signingIntentId } },
  );
}
