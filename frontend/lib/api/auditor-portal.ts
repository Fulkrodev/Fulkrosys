/**
 * Auditor portal public API client · Sesión 3B-2B.6 CLUSTER 2 Phase 4.
 *
 * Wraps backend `/api/v1/public/auditor-portal/{token}/*` (M09 public_api).
 *
 * Token-bounded · stateless per-request · 403 invalid · 410 expired/revoked
 * · 429 rate limited. Audit log emit hash chain inmutable (RLS protected
 * post Sub-atom 5.A b20f135).
 *
 * Mirror del lib/api/public-portals.ts pattern (pentester · remediation ·
 * verify-auth) · same security guarantees.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/public/auditor-portal";

export interface AuditorPortalCliente {
  client_id: string;
  razon_social: string;
  cif: string;
  primary_color: string;
  secondary_color: string;
  footer_text: string;
  has_logo: boolean;
}

export interface AuditorPortalProject {
  id: string;
  nombre: string;
  categoria: "BASICA" | "MEDIA" | "ALTA" | string;
  fase: string | null;
  lifecycle_state: string | null;
  certified_at: string | null;
  audit_passed_at: string | null;
  audit_result: "passed" | "observed" | "correction_required" | "failed" | null;
  audit_report_ref: string | null;
}

export interface AuditorPortalTokenMeta {
  expires_at: string | null;
  max_uses: number | null;
  current_uses: number;
}

export type AuditorPortalSection =
  | "summary"
  | "dda"
  | "magerit"
  | "plan"
  | "evidence"
  | "e041"
  | "audit-log"
  | "pentest"
  | "documents";

export interface AuditorPortalMetadata {
  cliente: AuditorPortalCliente;
  project: AuditorPortalProject;
  token_meta: AuditorPortalTokenMeta;
  available_sections: AuditorPortalSection[];
}

export interface AuditorPortalSessionStart {
  status: "ok";
  session_started_at: string;
  remaining_uses: number;
}

/** Fetch landing metadata · NO consume usos. 403/410/429 fail responses. */
export async function getAuditorPortalMetadata(
  token: string,
): Promise<AuditorPortalMetadata> {
  return api<AuditorPortalMetadata>(`${BASE}/${token}`);
}

/** Formal session start · consume 1 use · emit auditor.session.start. */
export async function startAuditorPortalSession(
  token: string,
): Promise<AuditorPortalSessionStart> {
  return api<AuditorPortalSessionStart>(`${BASE}/${token}/session`, {
    json: {},
  });
}

// ══════════════════════════════════════════════════════════════════════
// Phase 5 read-only views · Cluster A · Summary + DdA + MAGERIT
// ══════════════════════════════════════════════════════════════════════

export interface AuditorPortalSummaryCounts {
  dda_entries: number;
  evidence_files: number;
  magerit_analyses: number;
  pentest_runs: number;
}

export interface AuditorPortalSummary {
  cliente: AuditorPortalCliente;
  project: AuditorPortalProject;
  counts: AuditorPortalSummaryCounts;
}

export async function getAuditorPortalSummary(
  token: string,
): Promise<AuditorPortalSummary> {
  return api<AuditorPortalSummary>(`${BASE}/${token}/summary`);
}

export interface AuditorPortalDdaMedida {
  id: string;
  codigo: string;
  nombre: string;
  familia: string | null;
  descripcion: string | null;
  requisito_base: string | null;
  categoria_minima: string | null;
  aplicabilidad: string | null;
  justificacion_no_aplica: string | null;
  estado_implementacion: string | null;
  observaciones: string | null;
  aprobado_por: string | null;
  fecha_aprobacion: string | null;
  client_review_status: string | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
}

export interface AuditorPortalDda {
  project_id: string;
  filter_family: string | null;
  total: number;
  is_signed: boolean;
  signed_at: string | null;
  medidas: AuditorPortalDdaMedida[];
}

export async function getAuditorPortalDda(
  token: string,
  options?: { family?: string },
): Promise<AuditorPortalDda> {
  const params = options?.family ? `?family=${options.family}` : "";
  return api<AuditorPortalDda>(`${BASE}/${token}/dda${params}`);
}

export interface AuditorPortalMageritAnalysis {
  id: string;
  name: string;
  status: string;
  created_at: string | null;
  frozen_at: string | null;
}

export interface AuditorPortalMageritAsset {
  id: string;
  code: string;
  name: string;
  asset_type_code: string;
  owner: string | null;
  valuation: {
    d: number | null;
    i: number | null;
    c: number | null;
    a: number | null;
    t: number | null;
  };
  accumulated: {
    d: number | null;
    i: number | null;
    c: number | null;
    a: number | null;
    t: number | null;
  };
  client_review_status: string | null;
  client_reviewed_at: string | null;
}

export interface AuditorPortalMagerit {
  project_id: string;
  analysis: AuditorPortalMageritAnalysis | null;
  assets: AuditorPortalMageritAsset[];
  risks_total: number;
}

export async function getAuditorPortalMagerit(
  token: string,
): Promise<AuditorPortalMagerit> {
  return api<AuditorPortalMagerit>(`${BASE}/${token}/magerit`);
}

// ══════════════════════════════════════════════════════════════════════
// Phase 5 read-only views · Cluster B · Plan + Evidence + E-041
// ══════════════════════════════════════════════════════════════════════

export interface AuditorPortalPlanHeader {
  id: string;
  version: number;
  categoria: string | null;
  start_date: string | null;
  end_date_estimated: string | null;
  end_date_actual: string | null;
  total_effort_marcos_hours: number | null;
  total_effort_platform_hours: number | null;
  total_duration_weeks: number | null;
  critical_path_length_weeks: number | null;
  estado: string | null;
  baseline_date: string | null;
  aprobado_at: string | null;
}

export interface AuditorPortalPlanTask {
  id: string;
  task_code: string;
  task_name: string;
  phase: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_days: number | null;
  effort_marcos_hours: number | null;
  responsible: string | null;
  deliverable_e_code: string | null;
  status: string | null;
  is_critical_path: boolean;
  progress_pct: number;
}

export interface AuditorPortalPlan {
  project_id: string;
  plan: AuditorPortalPlanHeader | null;
  tasks: AuditorPortalPlanTask[];
}

export async function getAuditorPortalPlan(
  token: string,
): Promise<AuditorPortalPlan> {
  return api<AuditorPortalPlan>(`${BASE}/${token}/plan`);
}

export interface AuditorPortalEvidenceGroup {
  measure_code: string;
  total: number;
}

export interface AuditorPortalEvidenceItem {
  id: string;
  measure_code: string | null;
  evidence_type_id: string | null;
  nombre_tipo: string | null;
  fichero_nombre_original: string | null;
  fichero_mime_type: string | null;
  fichero_tamano_bytes: number | null;
  fecha_evidencia: string | null;
  fecha_caducidad: string | null;
  vigente: boolean;
  scan_status: string | null;
  hash_sha256: string | null;
}

export interface AuditorPortalEvidence {
  project_id: string;
  filter_measure_code: string | null;
  total_items: number;
  grouped_by_measure: AuditorPortalEvidenceGroup[];
  items: AuditorPortalEvidenceItem[];
}

export async function getAuditorPortalEvidence(
  token: string,
  options?: { measure_code?: string },
): Promise<AuditorPortalEvidence> {
  const params = options?.measure_code
    ? `?measure_code=${encodeURIComponent(options.measure_code)}`
    : "";
  return api<AuditorPortalEvidence>(`${BASE}/${token}/evidence${params}`);
}

export interface AuditorPortalE041Declaration {
  id: string;
  declaration_type: string;
  status: string;
  published_evidence_url: string | null;
  responsible_person_name: string | null;
  responsible_person_email: string | null;
  signed_at: string | null;
  signed_hash: string | null;
  anniversary_year: number | null;
  created_at: string | null;
  client_reviewed_at: string | null;
  client_concerns_note: string | null;
  is_signed: boolean;
}

export interface AuditorPortalE041 {
  project_id: string;
  total: number;
  declarations: AuditorPortalE041Declaration[];
}

export async function getAuditorPortalE041(
  token: string,
): Promise<AuditorPortalE041> {
  return api<AuditorPortalE041>(`${BASE}/${token}/e041`);
}

// ══════════════════════════════════════════════════════════════════════
// Phase 5 read-only views · Cluster C · Audit Log + Pentest + Documents
// ══════════════════════════════════════════════════════════════════════

export interface AuditorPortalAuditLogEntry {
  id: string;
  seq: number;
  tabla: string;
  accion: string;
  usuario: string | null;
  timestamp: string | null;
  payload_new: Record<string, unknown> | null;
  hash_current: string | null;
}

export interface AuditorPortalAuditLog {
  project_id: string;
  filter_accion: string | null;
  total_for_project: number;
  returned: number;
  limit: number;
  entries: AuditorPortalAuditLogEntry[];
}

export async function getAuditorPortalAuditLog(
  token: string,
  options?: { accion?: string; limit?: number },
): Promise<AuditorPortalAuditLog> {
  const qs = new URLSearchParams();
  if (options?.accion) qs.set("accion", options.accion);
  if (options?.limit) qs.set("limit", String(options.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return api<AuditorPortalAuditLog>(`${BASE}/${token}/audit-log${suffix}`);
}

export interface AuditorPortalPentestRun {
  id: string;
  category: string;
  mode: string;
  status: string;
  scheduled_start: string | null;
  completed_at: string | null;
  total_findings: number;
  confirmed_findings: number;
  severity_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  security_score: number | null;
  external_pentester_name: string | null;
  external_pentester_cert: string | null;
  created_at: string | null;
}

export interface AuditorPortalPentest {
  project_id: string;
  total_runs: number;
  runs: AuditorPortalPentestRun[];
}

export async function getAuditorPortalPentest(
  token: string,
): Promise<AuditorPortalPentest> {
  return api<AuditorPortalPentest>(`${BASE}/${token}/pentest`);
}

export interface AuditorPortalDocumentRun {
  id: string;
  estado: string;
  categoria: string;
  created_at: string | null;
  dossier_generated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  signed_zip_available: boolean;
}

export interface AuditorPortalDocuments {
  project_id: string;
  total_runs: number;
  runs: AuditorPortalDocumentRun[];
  signed_zip_endpoint: string;
}

export async function getAuditorPortalDocuments(
  token: string,
): Promise<AuditorPortalDocuments> {
  return api<AuditorPortalDocuments>(`${BASE}/${token}/documents`);
}
