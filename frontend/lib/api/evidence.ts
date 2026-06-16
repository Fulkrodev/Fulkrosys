/**
 * Motor 7 — Evidence API client.
 *
 * 6 endpoints reales (zero-mock). Usa el wrapper `api()` con CSRF +
 * credentials. Tipos espejo de los Pydantic schemas en
 * `backend/app/motors/m07_evidence/api.py`.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

// ─── Response types (mirror Pydantic) ────────────────────────────────

export interface PublicKeyResponse {
  algorithm: string;
  public_key_pem: string;
}

export interface UploadResponse {
  evidence_id: string;
  hash_sha256: string;
  firma_ed25519_hex: string;
  fichero_path: string;
  fecha_caducidad: string | null;
}

export interface EvidenceListItem {
  id: string;
  evidence_type_id: string | null;
  nombre_tipo: string | null;
  measure_code: string | null;
  fichero_nombre_original: string | null;
  fichero_mime_type: string | null;
  fecha_evidencia: string | null;
  fecha_caducidad: string | null;
  vigente: boolean;
  hash_sha256: string | null;
}

export interface EvidenceListResponse {
  total: number;
  items: EvidenceListItem[];
}

export interface FreshnessItemResponse {
  evidence_id: string;
  measure_code: string | null;
  fecha_caducidad: string | null;
  estado: string;
  dias_restantes: number | null;
}

export interface FreshnessResponse {
  project_id: string;
  total: number;
  vigentes: number;
  proxima_caducidad: number;
  caducadas: number;
  sin_caducidad: number;
  items: FreshnessItemResponse[];
}

export interface RenewalResponse {
  renewal_id: string | null;
  evidence_id: string;
  created: boolean;
  already_pending: boolean;
  motivo: string | null;
  error: string | null;
}

export interface VerificationResponse {
  evidence_id: string;
  verdict: string;
  hash_matches: boolean | null;
  signature_valid: boolean | null;
  detail: string | null;
}

export interface EvidenceTypeOption {
  id: string;
  label: string;
  descripcion: string;
  categoria: string;
  allowed_mime: string[];
  allowed_extensions: string[];
  max_size_mb: number;
  caducidad_dias: number | null;
  medidas_asociadas: string[];
}

export interface MeasureOption {
  codigo: string;
  nombre: string;
  familia: string | null;
}

export interface UploadCatalogResponse {
  project_id: string;
  categoria: string | null;
  evidence_types: EvidenceTypeOption[];
  measures: MeasureOption[];
}

// ─── Filters ─────────────────────────────────────────────────────────

export interface ListEvidenceFilters {
  measure_code?: string;
  evidence_type_id?: string;
  vigente?: boolean;
}

// ─── Endpoints ───────────────────────────────────────────────────────

/** GET /api/v1/evidence/public-key */
export async function getPublicKey(): Promise<PublicKeyResponse> {
  return api<PublicKeyResponse>(`${BASE}/evidence/public-key`);
}

/** POST /api/v1/evidence/projects/{projectId}/upload (multipart) */
export async function uploadEvidence(
  projectId: string,
  payload: {
    file: File;
    evidence_type_id: string;
    measure_code: string;
    obligation_id?: string;
  },
): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", payload.file);
  fd.append("evidence_type_id", payload.evidence_type_id);
  fd.append("measure_code", payload.measure_code);
  if (payload.obligation_id) fd.append("obligation_id", payload.obligation_id);

  // Note: api() wrapper attaches CSRF on POST; we omit json so it sends FormData
  return api<UploadResponse>(
    `${BASE}/evidence/projects/${projectId}/upload`,
    { method: "POST", body: fd },
  );
}

/** GET /api/v1/evidence/projects/{projectId}/upload-catalog (admin) */
export async function getUploadCatalog(
  projectId: string,
): Promise<UploadCatalogResponse> {
  return api<UploadCatalogResponse>(
    `${BASE}/evidence/projects/${projectId}/upload-catalog`,
  );
}

/** GET /api/v1/evidence/projects/{projectId}/list */
export async function listEvidence(
  projectId: string,
  filters: ListEvidenceFilters = {},
): Promise<EvidenceListResponse> {
  const qs = new URLSearchParams();
  if (filters.measure_code) qs.set("measure_code", filters.measure_code);
  if (filters.evidence_type_id) qs.set("evidence_type_id", filters.evidence_type_id);
  if (filters.vigente !== undefined) qs.set("vigente", String(filters.vigente));
  const q = qs.toString();
  return api<EvidenceListResponse>(
    `${BASE}/evidence/projects/${projectId}/list${q ? `?${q}` : ""}`,
  );
}

/** GET /api/v1/evidence/projects/{projectId}/expiring */
export async function getExpiringEvidence(
  projectId: string,
  warningDays = 30,
): Promise<FreshnessResponse> {
  return api<FreshnessResponse>(
    `${BASE}/evidence/projects/${projectId}/expiring?warning_days=${warningDays}`,
  );
}

/** POST /api/v1/evidence/projects/{projectId}/evidence/{evidenceId}/renew */
export async function renewEvidence(
  projectId: string,
  evidenceId: string,
  motivo?: string,
): Promise<RenewalResponse> {
  const qs = motivo ? `?motivo=${encodeURIComponent(motivo)}` : "";
  return api<RenewalResponse>(
    `${BASE}/evidence/projects/${projectId}/evidence/${evidenceId}/renew${qs}`,
    { method: "POST", json: {} },
  );
}

/** GET /api/v1/evidence/projects/{projectId}/evidence/{evidenceId}/verify */
export async function verifyEvidence(
  projectId: string,
  evidenceId: string,
): Promise<VerificationResponse> {
  return api<VerificationResponse>(
    `${BASE}/evidence/projects/${projectId}/evidence/${evidenceId}/verify`,
  );
}
