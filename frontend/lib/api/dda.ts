/**
 * Motor 3 — DdA API client (zero-mock).
 *
 * Tres rangos de endpoints:
 * 1. Admin status (existing FASE 9.D · GenerateDocumentButton gate):
 *    - getDdaStatus
 * 2. Admin gestión completa (sub-atom 1.D.F.A v3.11):
 *    - listAdminDdaEntries · getAdminDdaStats · generateAdminDda
 *    - updateAdminDdaEntry · freezeAdminDda · unfreezeAdminDda
 *    - getAdminMeasuresCatalog · getAdminEntryByMeasure
 *    - requestE040Signature · getE040SignatureStatus
 * 3. Cliente in-portal (SAN-E v3.MB-5.3 · cliente revisa 73 medidas):
 *    - getClientDdaSummary · listClientDdaMeasures · etc.
 *
 * Usa api()/clientApi() wrappers con CSRF + credentials cookie session.
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";

const BASE = "/api/v1";

// ════════════════════════════════════════════════════════════════════
// Admin status endpoint (FASE 9.D · existing)
// ════════════════════════════════════════════════════════════════════

export interface DdaStatusResponse {
  project_id: string;
  exists: boolean;
  frozen: boolean;
  frozen_at: string | null;
  frozen_by: string | null;
  total_entries: number;
  approved_entries: number;
}

/** GET /api/v1/dda/projects/{project_id}/status (FASE 9.D). */
export async function getDdaStatus(projectId: string): Promise<DdaStatusResponse> {
  return api<DdaStatusResponse>(`${BASE}/dda/projects/${projectId}/status`);
}

// ════════════════════════════════════════════════════════════════════
// Admin gestión completa (sub-atom 1.D.F.A v3.11)
// ════════════════════════════════════════════════════════════════════

export type DdaCategoriaSistema = "BASICA" | "MEDIA" | "ALTA";

export type DdaEstadoImplementacion =
  | "no_valorado"
  | "no_aplica"
  | "no_implantada"
  | "parcial"
  | "implantada";

export type DdaMarco = "org" | "op" | "mp";

export interface DdaAdminEntry {
  id: string;
  project_id: string;
  measure_codigo: string;
  measure_nombre: string;
  measure_marco: string;
  measure_familia: string | null;
  aplicabilidad: string;
  estado_implementacion: string;
  justificacion_no_aplica: string | null;
  refuerzos_aplicados: string[] | null;
  magerit_safeguards: string[];
  responsable: string | null;
  observaciones: string | null;
  version: number | null;
  aprobado_por: string | null;
  fecha_aprobacion: string | null;
}

export interface DdaAdminStats {
  project_id: string;
  total_medidas: number;
  total_aplicables: number;
  no_aplica: number;
  implantadas: number;
  parcial: number;
  no_implantadas: number;
  no_valoradas: number;
  completion_pct: number;
}

export interface DdaGenerateRequest {
  project_id: string;
  system_category: DdaCategoriaSistema;
  responsable?: string | null;
}

export interface DdaGenerateResult {
  project_id: string;
  system_category: DdaCategoriaSistema;
  total_entries: number;
  aplicables: number;
  no_aplica: number;
}

export interface DdaEntryUpdate {
  estado_implementacion?: DdaEstadoImplementacion;
  justificacion_no_aplica?: string | null;
  refuerzos_aplicados?: string[] | null;
  responsable?: string | null;
  observaciones?: string | null;
}

export interface DdaEntryUpdateResult {
  id: string;
  version: number | null;
  updated: boolean;
}

export interface DdaFreezeResult {
  project_id: string;
  aprobado_por: string;
  fecha_aprobacion: string;
  frozen_entries: number;
}

export interface DdaCatalogMeasure {
  codigo: string;
  nombre: string;
  marco: string;
  familia: string | null;
  descripcion?: string | null;
  categoria_minima?: string | null;
}

/** GET /api/v1/dda/projects/{project_id}/entries (filtrable marco/familia). */
export async function listAdminDdaEntries(
  projectId: string,
  filters?: { marco?: DdaMarco; familia?: string },
): Promise<DdaAdminEntry[]> {
  const params = new URLSearchParams();
  if (filters?.marco) params.set("marco", filters.marco);
  if (filters?.familia) params.set("familia", filters.familia);
  const qs = params.toString();
  const path = `${BASE}/dda/projects/${projectId}/entries${qs ? `?${qs}` : ""}`;
  return api<DdaAdminEntry[]>(path);
}

/** GET /api/v1/dda/projects/{project_id}/stats. */
export async function getAdminDdaStats(
  projectId: string,
): Promise<DdaAdminStats> {
  return api<DdaAdminStats>(`${BASE}/dda/projects/${projectId}/stats`);
}

/** POST /api/v1/dda/generate · crea DdA 73 entries. */
export async function generateAdminDda(
  body: DdaGenerateRequest,
): Promise<DdaGenerateResult> {
  return api<DdaGenerateResult>(`${BASE}/dda/generate`, {
    method: "POST",
    json: body,
  });
}

/** PATCH /api/v1/dda/entries/{entry_id}. */
export async function updateAdminDdaEntry(
  entryId: string,
  updates: DdaEntryUpdate,
): Promise<DdaEntryUpdateResult> {
  return api<DdaEntryUpdateResult>(`${BASE}/dda/entries/${entryId}`, {
    method: "PATCH",
    json: updates,
  });
}

/** POST /api/v1/dda/projects/{project_id}/freeze?aprobado_por={name}. */
export async function freezeAdminDda(
  projectId: string,
  aprobadoPor: string,
): Promise<DdaFreezeResult> {
  const path = `${BASE}/dda/projects/${projectId}/freeze?aprobado_por=${encodeURIComponent(aprobadoPor)}`;
  return api<DdaFreezeResult>(path, { method: "POST" });
}

/** POST /api/v1/dda/projects/{project_id}/unfreeze (204). */
export async function unfreezeAdminDda(projectId: string): Promise<void> {
  await api<void>(`${BASE}/dda/projects/${projectId}/unfreeze`, {
    method: "POST",
  });
}

/** GET /api/v1/dda/measures/catalog · read-only catálogo Anexo II. */
export async function getAdminMeasuresCatalog(
  marco?: DdaMarco,
): Promise<DdaCatalogMeasure[]> {
  const path = marco
    ? `${BASE}/dda/measures/catalog?marco=${marco}`
    : `${BASE}/dda/measures/catalog`;
  return api<DdaCatalogMeasure[]>(path);
}

/** GET /api/v1/dda/projects/{project_id}/measures/{measure_codigo}. */
export async function getAdminEntryByMeasure(
  projectId: string,
  measureCodigo: string,
): Promise<DdaAdminEntry> {
  return api<DdaAdminEntry>(
    `${BASE}/dda/projects/${projectId}/measures/${measureCodigo}`,
  );
}

// ════════════════════════════════════════════════════════════════════
// E-040 signature integration (M3-G2 existing · re-export para admin UI)
// ════════════════════════════════════════════════════════════════════

export interface E040SignatureRequest {
  recipient_email: string;
  recipient_name?: string | null;
  recipient_role?: string;
}

export interface E040SignatureResponse {
  link_id: string;
  magic_link_url: string;
  otp: string;
  expires_at: string;
  recipient_email: string;
  previous_link_revoked: boolean;
  dda_snapshot_hash: string;
  frozen_at: string;
  total_entries: number;
}

export interface E040SignatureStatus {
  project_id: string;
  has_signature_request: boolean;
  is_frozen: boolean;
  total_entries: number;
  link_id: string | null;
  state: string | null;
  issued_at: string | null;
  expires_at: string | null;
  consumed_at: string | null;
  recipient_email: string | null;
}

/** POST /api/v1/dda/projects/{project_id}/e040/request-signature. */
export async function requestE040Signature(
  projectId: string,
  body: E040SignatureRequest,
): Promise<E040SignatureResponse> {
  return api<E040SignatureResponse>(
    `${BASE}/dda/projects/${projectId}/e040/request-signature`,
    { method: "POST", json: body },
  );
}

/** GET /api/v1/dda/projects/{project_id}/e040/signature-status. */
export async function getE040SignatureStatus(
  projectId: string,
): Promise<E040SignatureStatus> {
  return api<E040SignatureStatus>(
    `${BASE}/dda/projects/${projectId}/e040/signature-status`,
  );
}

// ════════════════════════════════════════════════════════════════════
// Labels canonical (sub-atom 1.D.F.A v3.11 · UI consistente)
// ════════════════════════════════════════════════════════════════════

export const DDA_ESTADO_LABELS: Record<string, string> = {
  no_valorado: "No valorado",
  no_aplica: "No aplica",
  no_implantada: "No implantada",
  parcial: "Parcial",
  implantada: "Implantada",
};

export const DDA_ESTADO_VARIANT: Record<
  string,
  "secondary" | "danger" | "outline" | "info" | "success"
> = {
  no_valorado: "secondary",
  no_aplica: "outline",
  no_implantada: "danger",
  parcial: "info",
  implantada: "success",
};

export const DDA_MARCO_LABELS: Record<DdaMarco, string> = {
  org: "Organizativo",
  op: "Operacional",
  mp: "Protección",
};

// ════════════════════════════════════════════════════════════════════
// Cliente in-portal endpoints (SAN-E v3.MB-5.3)
// ════════════════════════════════════════════════════════════════════

export type DdaFamily = "org" | "op" | "mp";

export type DdaClientReviewStatus =
  | "pendiente_revision"
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export type DdaClientReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export interface DdaClientSummary {
  project_id: string;
  categoria_objetivo: string | null;
  total_measures: number;
  reviewed_count: number;
  pending_review_count: number;
  questions_count: number;
  suggestions_count: number;
  completion_percentage: number;
  is_frozen: boolean;
  frozen_at: string | null;
  last_signed_at: string | null;
  ready_for_final_sign: boolean;
}

export interface EvidenceSummary {
  id: string;
  nombre_tipo: string | null;
  fichero_nombre_original: string | null;
  fichero_mime_type: string | null;
  fecha_evidencia: string | null;
  vigente: boolean;
}

export interface DdaClientEntryView {
  // Identificacion
  id: string;
  measure_codigo: string;
  measure_nombre: string;
  measure_familia: string | null;
  measure_subfamilia: string | null;
  measure_descripcion: string | null;

  // ENS context educational (atom 5.3.E)
  requisito_base: string | null;
  ccn_stic_reference: string | null;
  categoria_minima: string | null;
  tier_required_for: string[];
  dimensiones_aplicables: string[] | null;

  // Estado admin (cliente VE · NO edit)
  aplicabilidad: string | null;
  justificacion_no_aplica: string | null;
  estado_implementacion: string | null;
  observaciones: string | null;
  aprobado_por: string | null;
  fecha_aprobacion: string | null;

  // Evidencias linked
  evidence_count: number;
  evidence_list: EvidenceSummary[];

  // Cliente review
  client_review_status: DdaClientReviewStatus | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
}

/** GET /api/v1/portal/dda/projects/{project_id} · cliente summary. */
export async function getClientDdaSummary(
  projectId: string,
): Promise<DdaClientSummary> {
  return clientApi<DdaClientSummary>(`/portal/dda/projects/${projectId}`);
}

/** GET /api/v1/portal/dda/projects/{project_id}/measures · cliente list. */
export async function listClientDdaMeasures(
  projectId: string,
  filters?: { family?: DdaFamily; review_status?: DdaClientReviewStatus },
): Promise<DdaClientEntryView[]> {
  const params = new URLSearchParams();
  if (filters?.family) params.set("family", filters.family);
  if (filters?.review_status) params.set("review_status", filters.review_status);
  const qs = params.toString();
  const path = `/portal/dda/projects/${projectId}/measures${qs ? `?${qs}` : ""}`;
  return clientApi<DdaClientEntryView[]>(path);
}

/** GET /api/v1/portal/dda/entries/{entry_id} · cliente entry detail. */
export async function getClientDdaEntryDetail(
  entryId: string,
): Promise<DdaClientEntryView> {
  return clientApi<DdaClientEntryView>(`/portal/dda/entries/${entryId}`);
}

/** POST /api/v1/portal/dda/entries/{entry_id}/review · cliente review action. */
export async function reviewClientDdaEntry(
  entryId: string,
  action: DdaClientReviewAction,
  note?: string,
): Promise<DdaClientEntryView> {
  return clientApi<DdaClientEntryView>(`/portal/dda/entries/${entryId}/review`, {
    method: "POST",
    json: { action, note: note ?? null },
  });
}
