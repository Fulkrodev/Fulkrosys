/**
 * Motor 27 - Conformity Lifecycle API client.
 *
 * 29 endpoints reales (zero-mock):
 *   - 14 endpoints en `/api/v1/conformity` (api.py)
 *   - 15 endpoints en `/api/v1/projects/{id}/conformity` (api_paso5.py)
 *
 * Tipos espejo de los Pydantic schemas en `backend/app/motors/m27_conformity/`.
 *
 * Usa `api()` wrapper con CSRF + credentials.
 */
import { api } from "@/lib/api";

const BASE_LIFECYCLE = "/api/v1/conformity";
const BASE_PASO5 = "/api/v1";

// =====================================================================
// Tipos compartidos (espejo Pydantic)
// =====================================================================

export type RouteType = "DECLARATION" | "CERTIFICATION";
export type RouteState =
  | "DRAFT"
  | "LOCKED"
  | "PREPARING"
  | "SUBMITTED"
  | "AUDITED"
  | "CONFORMANT";
export type CategoryLevel = "BASICA" | "MEDIA" | "ALTA";
export type SubmissionState =
  | "GENERATED"
  | "PENDING"
  | "SUBMITTED"
  | "COMPLETED"
  | "REJECTED";
export type SubmissionTarget =
  | "AUDITOR"
  | "REGISTRO"
  | "AAPP"
  | "PILAR"
  | "LUCIA"
  | "INES";
export type ExportTool = "PILAR" | "LUCIA" | "INES" | "Registro";
export type RenewalStateBackend =
  | "T-180"
  | "T-120"
  | "T-90"
  | "T-60"
  | "T-30"
  | "DUE"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "LAPSED";

// ----- Conformity Route -----

export interface ConformityRouteOut {
  project_id: string;
  route_type: RouteType;
  state: RouteState;
  category: string;
  overlay_code: string | null;
  locked_at: string | null;
  next_review_due: string | null;
}

export interface ConformityStatusOut {
  project_id: string;
  route: ConformityRouteOut | null;
  submissions_count: number;
  pending_submissions: number;
  renewal_state: string | null;
  next_renewal_due: string | null;
  invariants_ok: boolean;
  invariant_violations: string[];
}

export interface RouteLockBody {
  route_type: RouteType;
  category: CategoryLevel;
  overlay_code?: string | null;
  rationale: string;
}

export interface RouteHistoryEntry {
  from_state: string | null;
  to_state: string;
  at: string;
  rationale: string | null;
}

export interface RouteHistoryResponse {
  project_id: string;
  history: RouteHistoryEntry[];
}

// ----- Declaration -----

export interface DeclarationGenerateBody {
  requested_by: string;
  notes?: string | null;
}

export interface DeclarationOut {
  project_id: string;
  declaration_id: string;
  documents: string[];
  generated_at: string;
  state: "draft" | "ready_for_signature" | "signed";
}

// ----- Submission -----

export interface SubmissionCreateBody {
  target: SubmissionTarget;
  payload_template: string;
  justification?: string | null;
}

export interface SubmissionOut {
  submission_id: string;
  project_id: string;
  target: string;
  state: SubmissionState;
  payload_present: boolean;
  proof_present: boolean;
  created_at: string;
  submitted_at: string | null;
  completed_at: string | null;
}

export interface SubmissionProofBody {
  proof_type: "pdf" | "zip" | "screenshot" | "registry_id";
  proof_reference: string;
  completed?: boolean;
}

// ----- Renewal -----

export interface RenewalCampaignOut {
  project_id: string;
  state: RenewalStateBackend;
  target_renewal_date: string;
  days_remaining: number;
  actions_required: string[];
}

// ----- External Export -----

export interface ExternalExportCreateBody {
  tool: ExportTool;
  params?: Record<string, unknown>;
}

export interface ExternalExportOut {
  export_id: string;
  tool: string;
  artifact_path: string;
  artifact_hash: string;
  checklist: string[];
  created_at: string;
  proof_uploaded: boolean;
}

// ----- PCE Overlay -----

export interface PceOverlayOut {
  project_id: string;
  overlay_code: string | null;
  overlay_name: string | null;
  extra_controls: string[];
  detection_confidence: number;
  rationale: string | null;
}

export interface PceOverlayValidateResult {
  ok: boolean;
  reason?: string;
  [key: string]: unknown;
}

// ----- Paso 5: status -----

export interface ConformityStatusPaso5 {
  route: {
    id?: string;
    route_type?: string;
    status?: string;
    expiration_date?: string | null;
    metadata?: Record<string, unknown>;
  } | null;
  declarations?: { id: string; status: string; signed_hash: string | null }[];
  submissions?: { id: string; submission_type: string; status: string }[];
  material_changes?: { id: string; is_material: boolean; score: number }[];
  recategorizations?: { id: string; status: string }[];
  overlays?: { id: string; overlay_type: string; compliance_status: string }[];
  role_topology?: { id: string; pattern: string } | null;
  next_renewal?: {
    id: string;
    campaign_type: string;
    scheduled_for: string | null;
    status: string;
  } | null;
  [key: string]: unknown;
}

// ----- Paso 5 bodies -----

export interface InitializeRouteBody {
  overlay_hints?: string[];
}

export interface BasicDeclarationBody {
  responsible_person_name: string;
  responsible_person_email: string;
  published_url?: string | null;
  self_assessment_report_id?: string | null;
}

export interface EnacCertificationBody {
  auditor_entity: string;
  dossier_run_id?: string | null;
}

export interface MaterialChangeBody {
  change_type: string;
  description: string;
  answers: Record<string, boolean>;
  detected_by?: string;
}

export interface RecategorizeBody {
  old_category: string;
  new_category: string;
  trigger_material_change_id?: string | null;
  approved_by?: string | null;
}

export interface ApplyOverlayBody {
  overlay_type: string;
  assessment_report_id?: string | null;
}

export interface RoleTopologyGenerateBody {
  total_persons: number;
  roles_assigned: Record<string, unknown>;
  sector?: string | null;
  approved_by?: string | null;
}

export interface ClaraIngestBody {
  content_b64: string;
  report_filename?: string;
}

// =====================================================================
// API functions - lifecycle (api.py - 14 endpoints)
// =====================================================================

/** POST /api/v1/conformity/projects/{id}/route/lock */
export function lockRoute(
  projectId: string,
  body: RouteLockBody,
): Promise<ConformityRouteOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/route/lock`, {
    method: "POST",
    json: body,
  });
}

/** POST /api/v1/conformity/projects/{id}/route/revalidate */
export function revalidateRoute(
  projectId: string,
): Promise<ConformityRouteOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/route/revalidate`, {
    method: "POST",
  });
}

/** GET /api/v1/conformity/projects/{id}/status */
export function getConformityStatusLifecycle(
  projectId: string,
): Promise<ConformityStatusOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/status`);
}

/** GET /api/v1/conformity/projects/{id}/route/history */
export function getRouteHistory(
  projectId: string,
): Promise<RouteHistoryResponse> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/route/history`);
}

/** POST /api/v1/conformity/projects/{id}/declaration/generate */
export function generateDeclaration(
  projectId: string,
  body: DeclarationGenerateBody,
): Promise<DeclarationOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/declaration/generate`, {
    method: "POST",
    json: body,
  });
}

/** POST /api/v1/conformity/projects/{id}/submissions */
export function createSubmission(
  projectId: string,
  body: SubmissionCreateBody,
): Promise<SubmissionOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/submissions`, {
    method: "POST",
    json: body,
  });
}

/** POST /api/v1/conformity/projects/{id}/submissions/{sid}/submit-proof */
export function submitSubmissionProof(
  projectId: string,
  sid: string,
  body: SubmissionProofBody,
): Promise<SubmissionOut> {
  return api(
    `${BASE_LIFECYCLE}/projects/${projectId}/submissions/${sid}/submit-proof`,
    { method: "POST", json: body },
  );
}

/** POST /api/v1/conformity/projects/{id}/renewal/start?target_date=YYYY-MM-DD */
export function startRenewal(
  projectId: string,
  targetDate: string,
): Promise<RenewalCampaignOut> {
  const qs = `?target_date=${encodeURIComponent(targetDate)}`;
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/renewal/start${qs}`, {
    method: "POST",
  });
}

/** GET /api/v1/conformity/projects/{id}/renewal */
export function getRenewal(projectId: string): Promise<RenewalCampaignOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/renewal`);
}

/** POST /api/v1/conformity/projects/{id}/external-exports */
export function createExternalExport(
  projectId: string,
  body: ExternalExportCreateBody,
): Promise<ExternalExportOut> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/external-exports`, {
    method: "POST",
    json: body,
  });
}

/** GET /api/v1/conformity/projects/{id}/external-exports */
export function listExternalExports(
  projectId: string,
): Promise<ExternalExportOut[]> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/external-exports`);
}

/** POST /api/v1/conformity/projects/{id}/external-exports/{eid}/upload-proof?proof_reference=... */
export function uploadExportProof(
  projectId: string,
  eid: string,
  proofReference: string,
): Promise<ExternalExportOut> {
  const qs = `?proof_reference=${encodeURIComponent(proofReference)}`;
  return api(
    `${BASE_LIFECYCLE}/projects/${projectId}/external-exports/${eid}/upload-proof${qs}`,
    { method: "POST" },
  );
}

/** GET /api/v1/conformity/projects/{id}/pce-overlay?sector=...&category=... */
export function detectOverlay(
  projectId: string,
  sector = "generico",
  category: CategoryLevel = "BASICA",
): Promise<PceOverlayOut> {
  const qs = `?sector=${encodeURIComponent(sector)}&category=${encodeURIComponent(
    category,
  )}`;
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/pce-overlay${qs}`);
}

/** POST /api/v1/conformity/projects/{id}/pce-overlay/validate?overlay_code=...&project_category=... */
export function validateOverlay(
  projectId: string,
  overlayCode: string,
  projectCategory: string,
): Promise<PceOverlayValidateResult> {
  const qs = `?overlay_code=${encodeURIComponent(
    overlayCode,
  )}&project_category=${encodeURIComponent(projectCategory)}`;
  return api(
    `${BASE_LIFECYCLE}/projects/${projectId}/pce-overlay/validate${qs}`,
    { method: "POST" },
  );
}

// =====================================================================
// API functions - Paso 5 (api_paso5.py - 15 endpoints)
// =====================================================================

/** POST /api/v1/projects/{id}/conformity/initialize */
export function initializeConformity(
  projectId: string,
  body: InitializeRouteBody = {},
): Promise<{
  route_id: string;
  route_type: string;
  status: string;
  expiration_date: string | null;
  metadata: Record<string, unknown>;
}> {
  return api(`${BASE_PASO5}/projects/${projectId}/conformity/initialize`, {
    method: "POST",
    json: body,
  });
}

/** GET /api/v1/projects/{id}/conformity/status */
export function getConformityStatusPaso5(
  projectId: string,
): Promise<ConformityStatusPaso5> {
  return api(`${BASE_PASO5}/projects/${projectId}/conformity/status`);
}

/** POST /api/v1/projects/{id}/conformity/basic-declaration/submit */
export function submitBasicDeclaration(
  projectId: string,
  body: BasicDeclarationBody,
): Promise<{ declaration_id: string; signed_hash: string; status: string }> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/basic-declaration/submit`,
    { method: "POST", json: body },
  );
}

/** POST /api/v1/projects/{id}/conformity/enac-certification/prepare */
export function prepareEnacCertification(
  projectId: string,
  body: EnacCertificationBody,
): Promise<{ submission_id: string; status: string; auditor_entity: string }> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/enac-certification/prepare`,
    { method: "POST", json: body },
  );
}

/** POST /api/v1/projects/{id}/conformity/material-change/register */
export function registerMaterialChange(
  projectId: string,
  body: MaterialChangeBody,
): Promise<{
  material_change_id: string;
  materiality_score: number;
  is_material: boolean;
  triggered_extraordinary_audit: boolean;
  extraordinary_audit_id: string | null;
}> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/material-change/register`,
    { method: "POST", json: body },
  );
}

/** GET /api/v1/projects/{id}/conformity/material-changes */
export function listMaterialChanges(projectId: string): Promise<{
  count: number;
  materiality_tree_questions: { key: string; weight: number; text: string }[];
  items: {
    id: string;
    change_type: string;
    is_material: boolean;
    materiality_score: number;
    description: string;
    detected_at: string | null;
  }[];
}> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/material-changes`,
  );
}

/** POST /api/v1/projects/{id}/conformity/recategorize */
export function recategorize(
  projectId: string,
  body: RecategorizeBody,
): Promise<{
  recategorization_id: string;
  status: string;
  old: string;
  new: string;
}> {
  return api(`${BASE_PASO5}/projects/${projectId}/conformity/recategorize`, {
    method: "POST",
    json: body,
  });
}

/** POST /api/v1/projects/{id}/conformity/pce-overlay/apply */
export function applyOverlay(
  projectId: string,
  body: ApplyOverlayBody,
): Promise<{
  overlay_id: string;
  overlay_type: string;
  overlay_spec_version: string | null;
  extra_measures_count: number;
  compliance_status: string;
}> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/pce-overlay/apply`,
    { method: "POST", json: body },
  );
}

/** GET /api/v1/projects/{id}/conformity/role-topology */
export function getRoleTopology(projectId: string): Promise<{
  role_topology_id: string;
  pattern: string;
  total_persons: number;
  exceptions_count: number;
  approved_at: string | null;
  revision_date: string | null;
  roles_assigned: Record<string, unknown>;
}> {
  return api(`${BASE_PASO5}/projects/${projectId}/conformity/role-topology`);
}

/** POST /api/v1/projects/{id}/conformity/role-topology/generate */
export function generateRoleTopology(
  projectId: string,
  body: RoleTopologyGenerateBody,
): Promise<{
  role_topology_id: string;
  pattern: string;
  total_persons: number;
  exceptions_count: number;
}> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/role-topology/generate`,
    { method: "POST", json: body },
  );
}

/** POST /api/v1/projects/{id}/conformity/renewal/trigger?auto=true */
export function triggerRenewal(
  projectId: string,
  auto = true,
): Promise<{
  campaign_id: string;
  campaign_type: string;
  scheduled_for: string | null;
  status: string;
}> {
  const qs = `?auto=${auto ? "true" : "false"}`;
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/renewal/trigger${qs}`,
    { method: "POST" },
  );
}

/** GET /api/v1/projects/{id}/conformity/submissions */
export function listConformitySubmissions(projectId: string): Promise<{
  count: number;
  items: {
    id: string;
    submission_type: string;
    external_system: string | null;
    status: string;
    submitted_at: string | null;
    external_ref_id: string | null;
  }[];
}> {
  return api(`${BASE_PASO5}/projects/${projectId}/conformity/submissions`);
}

/** POST /api/v1/projects/{id}/conformity/adapters/pilar/export-mgr */
export function pilarExportMgr(projectId: string): Promise<{
  tool: string;
  artifact_path: string;
  artifact_hash: string;
  content_b64: string;
  checklist: string[];
}> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/adapters/pilar/export-mgr`,
    { method: "POST" },
  );
}

/** POST /api/v1/projects/{id}/conformity/adapters/ines/snapshot?year=YYYY */
export function inesSnapshot(
  projectId: string,
  year?: number,
): Promise<{
  tool: string;
  artifact_path: string;
  artifact_hash: string;
  year: number;
  size_bytes: number;
  sheets: string[];
  checklist: string[];
}> {
  const qs = typeof year === "number" ? `?year=${year}` : "";
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/adapters/ines/snapshot${qs}`,
    { method: "POST" },
  );
}

/** POST /api/v1/projects/{id}/conformity/adapters/clara/ingest */
export function claraIngest(
  projectId: string,
  body: ClaraIngestBody,
): Promise<Record<string, unknown>> {
  return api(
    `${BASE_PASO5}/projects/${projectId}/conformity/adapters/clara/ingest`,
    { method: "POST", json: body },
  );
}

// =====================================================================
// SAN-C.MB-9.bis · Distintivo + Declaración CCN-STIC 809
// =====================================================================

export interface CertIdInfo {
  project_id: string;
  cert_id: string;
  category: CategoryLevel | null;
  public_badge_url: string;
  issued_date: string | null;
  expiry_date: string | null;
}

/** GET /api/v1/conformity/projects/{id}/cert-id */
export function getCertIdInfo(projectId: string): Promise<CertIdInfo> {
  return api(`${BASE_LIFECYCLE}/projects/${projectId}/cert-id`);
}

/** Admin badge SVG URL (auth required) for preview pre-publicación. */
export function getAdminBadgeUrl(projectId: string): string {
  return `${BASE_LIFECYCLE}/projects/${projectId}/badge.svg`;
}

/** Public badge SVG URL (sin auth) embed-able en sede electrónica. */
export function getPublicBadgeUrl(certId: string): string {
  return `/api/v1/public/conformity/badge/${certId}/badge.svg`;
}

/**
 * POST /api/v1/conformity/projects/{id}/declaration/generate-docx
 *
 * Descarga DOCX Declaración Conformidad Básica (E-180 CCN-STIC 809).
 * Devuelve Blob (no JSON), por lo que NO usa api() wrapper · usa fetch
 * directo con credentials + CSRF.
 */
export async function generateDeclarationDocx(
  projectId: string,
): Promise<Blob> {
  const { CSRF_HEADER } = await import("@/lib/constants");
  const { getCsrfToken } = await import("@/lib/csrf");
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);

  const response = await fetch(
    `${BASE_LIFECYCLE}/projects/${projectId}/declaration/generate-docx`,
    { method: "POST", headers, credentials: "include" },
  );

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        detail = String((payload as { detail: unknown }).detail);
      }
    } catch {
      // not JSON · use statusText
    }
    throw new Error(detail);
  }

  return response.blob();
}