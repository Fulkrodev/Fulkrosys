/**
 * Motor 2 - MAGERIT v3 API client (zero-mock).
 *
 * 31 endpoints reales bajo /api/v1/magerit (router prefix).
 *
 * O2 · BASE decia "/api/v1" y el router se declara con prefijo propio
 * "/magerit" (backend/app/motors/m02_magerit/api.py), asi que las 30 llamadas
 * de este fichero daban 404 y la pagina de analisis de riesgos estaba muerta
 * entera. El prefijo se escribe una vez, aqui.
 * Tipos espejo de los Pydantic schemas en
 * backend/app/motors/m02_magerit/schemas.py.
 *
 * Usa api() wrapper con CSRF + credentials.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/magerit";

// ===================================================================
// Tipos compartidos (espejo Pydantic backend schemas.py)
// ===================================================================

export type CalculationMode = "qualitative" | "quantitative" | "hybrid";
export type AnalysisStatus =
  | "draft"
  | "in_progress"
  | "completed"
  | "approved";
export type ProbabilityLevel = "MB" | "B" | "M" | "A" | "MA";
export type RiskLevel = "MB" | "B" | "M" | "A" | "MA";
export type Dimension = "D" | "I" | "C" | "A" | "T";
export type SafeguardEffectType = "preventive" | "palliative" | "both";
export type SafeguardStatus = "planned" | "partial" | "deployed" | "verified";
export type TreatmentType =
  | "mitigar"
  | "transferir"
  | "aceptar"
  | "eliminar";
export type TreatmentStatus = "pending" | "in_progress" | "completed";

// ----- Analysis -----

export interface AnalysisCreateBody {
  name: string;
  calculation_mode?: CalculationMode;
  description?: string | null;
}

export interface AnalysisOut {
  id: string;
  project_id: string;
  name: string;
  version: number;
  status: AnalysisStatus;
  calculation_mode: CalculationMode;
  methodology_version: string;
  notes: string | null;
  created_at: string;
}

// ----- Assets -----

export interface AssetIn {
  code: string;
  name: string;
  asset_type_code: string;
  description?: string | null;
  owner?: string | null;
  value_d?: number;
  value_i?: number;
  value_c?: number;
  value_a?: number;
  value_t?: number;
}

export interface AssetOut {
  id: string;
  code: string;
  name: string;
  asset_type_code: string;
  value_d: number | null;
  value_i: number | null;
  value_c: number | null;
  value_a: number | null;
  value_t: number | null;
  accumulated_d: number | null;
  accumulated_i: number | null;
  accumulated_c: number | null;
  accumulated_a: number | null;
  accumulated_t: number | null;
}

export interface AssetInventoryRequest {
  assets: AssetIn[];
}

// ----- Dependencies -----

export interface DependencyIn {
  superior_asset_id: string;
  inferior_asset_id: string;
  dependency_degree?: number;
  reason?: string | null;
}

export interface DependencyGraphRequest {
  dependencies: DependencyIn[];
}

// ----- Threats -----

export interface ThreatAssessmentIn {
  asset_id: string;
  threat_code: string;
  probability: ProbabilityLevel;
  degradation_d?: number;
  degradation_i?: number;
  degradation_c?: number;
  degradation_a?: number;
  degradation_t?: number;
}

export interface ThreatAssessmentRequest {
  assessments: ThreatAssessmentIn[];
}

// ----- Safeguards -----

export interface SafeguardDeploymentIn {
  safeguard_code: string;
  efficacy?: number;
  effect_type?: SafeguardEffectType;
  status?: SafeguardStatus;
  responsible?: string | null;
  notes?: string | null;
}

export interface SafeguardDeploymentRequest {
  deployments: SafeguardDeploymentIn[];
}

// ----- Risk calculations -----

export interface RiskCalculationOut {
  asset_id: string;
  threat_code: string;
  dimension: Dimension;
  impact_intrinsic: number | null;
  risk_intrinsic_accumulated: number | null;
  risk_intrinsic_repercuted: number | null;
  impact_effective: number | null;
  risk_effective: number | null;
  risk_residual: number | null;
  risk_level: string | null;
}

// ----- Treatment plan -----

export interface TreatmentPlanRequest {
  risk_tolerance_threshold?: RiskLevel;
}

export interface TreatmentActionOut {
  id: string;
  asset_id: string;
  threat_code: string;
  dimension: Dimension;
  current_risk_level: string;
  current_risk_value: number | null;
  treatment: TreatmentType;
  action_description: string | null;
  proposed_safeguards: string[] | null;
  target_risk_level: string | null;
  responsible: string | null;
  deadline: string | null;
  status: TreatmentStatus;
}

// ----- Report -----

export interface AnalysisReportOut {
  analysis: AnalysisOut;
  assets: AssetOut[];
  risk_calculations: RiskCalculationOut[];
  treatment_actions: TreatmentActionOut[];
  summary: Record<string, unknown>;
}

// ----- Operation result -----

export interface OperationResult {
  analysis_id: string;
  operation: string;
  rows_affected: number;
  message: string;
}

// ----- Signature E028 -----

export interface RequestE028SignatureBody {
  recipient_email: string;
  recipient_name?: string | null;
  recipient_role?: string;
}

export interface RequestE028SignatureResponse {
  link_id: string;
  magic_link_url: string;
  otp: string;
  expires_at: string;
  recipient_email: string;
  previous_link_revoked: boolean;
  report_snapshot_hash: string;
  frozen_at: string;
}

export interface E028SignatureStatusResponse {
  analysis_id: string;
  has_signature_request: boolean;
  is_frozen: boolean;
  link_id: string | null;
  state: string | null;
  issued_at: string | null;
  expires_at: string | null;
  consumed_at: string | null;
  recipient_email: string | null;
}

// ===================================================================
// 1. Analysis lifecycle
// ===================================================================

export function createAnalysis(
  projectId: string,
  body: AnalysisCreateBody,
): Promise<AnalysisOut> {
  return api<AnalysisOut>(`${BASE}/projects/${projectId}/analysis`, {
    method: "POST",
    json: body,
  });
}

/**
 * El analisis MAGERIT vigente del proyecto, o `null` si aun no hay ninguno.
 * Responde 200 con cuerpo null cuando no existe: "todavia no hay analisis" es
 * un estado normal del ciclo ENS, no un error.
 */
export function getProjectAnalysis(
  projectId: string,
): Promise<AnalysisOut | null> {
  return api<AnalysisOut | null>(`${BASE}/projects/${projectId}/analysis`);
}

export function softDeleteAnalysis(analysisId: string): Promise<void> {
  return api<void>(`${BASE}/analysis/${analysisId}`, { method: "DELETE" });
}

// ===================================================================
// 2. Assets / Dependencies / Threats / Safeguards
// ===================================================================

export function loadAssets(
  analysisId: string,
  body: AssetInventoryRequest,
): Promise<AssetOut[]> {
  return api<AssetOut[]>(`${BASE}/analysis/${analysisId}/assets`, {
    method: "POST",
    json: body,
  });
}

export function importAssets(
  analysisId: string,
  body: AssetInventoryRequest,
): Promise<OperationResult> {
  return api<OperationResult>(
    `${BASE}/analysis/${analysisId}/assets/import`,
    { method: "POST", json: body },
  );
}

export function loadDependencies(
  analysisId: string,
  body: DependencyGraphRequest,
): Promise<OperationResult> {
  return api<OperationResult>(
    `${BASE}/analysis/${analysisId}/dependencies`,
    { method: "POST", json: body },
  );
}

export function propagateValues(
  analysisId: string,
): Promise<OperationResult> {
  return api<OperationResult>(`${BASE}/analysis/${analysisId}/propagate`, {
    method: "POST",
    json: {},
  });
}

export function loadThreats(
  analysisId: string,
  body: ThreatAssessmentRequest,
): Promise<OperationResult> {
  return api<OperationResult>(`${BASE}/analysis/${analysisId}/threats`, {
    method: "POST",
    json: body,
  });
}

export function deploySafeguards(
  analysisId: string,
  body: SafeguardDeploymentRequest,
): Promise<OperationResult> {
  return api<OperationResult>(
    `${BASE}/analysis/${analysisId}/safeguards`,
    { method: "POST", json: body },
  );
}

// ===================================================================
// 3. Risk calculations
// ===================================================================

export function calculateIntrinsicRisk(
  analysisId: string,
): Promise<OperationResult> {
  return api<OperationResult>(
    `${BASE}/analysis/${analysisId}/calculate-intrinsic`,
    { method: "POST", json: {} },
  );
}

export function calculateEffectiveRisk(
  analysisId: string,
): Promise<OperationResult> {
  return api<OperationResult>(
    `${BASE}/analysis/${analysisId}/calculate-effective`,
    { method: "POST", json: {} },
  );
}

export function calculateResidualRisk(
  analysisId: string,
): Promise<OperationResult> {
  return api<OperationResult>(
    `${BASE}/analysis/${analysisId}/calculate-residual`,
    { method: "POST", json: {} },
  );
}

// ===================================================================
// 4. Treatment plan
// ===================================================================

export function generateTreatmentPlan(
  analysisId: string,
  body: TreatmentPlanRequest = {},
): Promise<TreatmentActionOut[]> {
  return api<TreatmentActionOut[]>(
    `${BASE}/analysis/${analysisId}/treatment-plan`,
    { method: "POST", json: body },
  );
}

// ===================================================================
// 5. Reports & freeze
// ===================================================================

export function getAnalysisReport(
  analysisId: string,
): Promise<AnalysisReportOut> {
  return api<AnalysisReportOut>(`${BASE}/analysis/${analysisId}/report`);
}

export function freezeAnalysis(analysisId: string): Promise<unknown> {
  return api<unknown>(`${BASE}/analysis/${analysisId}/freeze`, {
    method: "POST",
    json: {},
  });
}

export function unfreezeAnalysis(analysisId: string): Promise<void> {
  return api<void>(`${BASE}/analysis/${analysisId}/unfreeze`, {
    method: "POST",
    json: {},
  });
}

export function getAnalysisSnapshot(
  analysisId: string,
): Promise<unknown> {
  return api<unknown>(`${BASE}/analysis/${analysisId}/snapshot`);
}

// ===================================================================
// 6. Document exports (XML, PDF, DOCX, MGR, PILAR deprecated)
// ===================================================================

export function exportAnalysisXmlUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export-xml`;
}

export function getReportPdfUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/report.pdf`;
}

export function getReportDocxUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/report.docx`;
}

export function exportPilarDeprecatedUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export-pilar`;
}

export function exportAnalysisMgrUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export-mgr`;
}

// ===================================================================
// 7. Excel exports (7 worksheets)
// ===================================================================

export function downloadAssetInventoryUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/assets.xlsx`;
}

export function downloadDependencyMapUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/dependencies.xlsx`;
}

export function downloadThreatAssessmentUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/threats.xlsx`;
}

export function downloadSafeguardDeploymentUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/safeguards.xlsx`;
}

export function downloadRiskCalculationsUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/risks.xlsx`;
}

export function downloadTreatmentPlanUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/treatment.xlsx`;
}

export function downloadExecutiveSummaryUrl(analysisId: string): string {
  return `${BASE}/analysis/${analysisId}/export/summary.xlsx`;
}

// ===================================================================
// 8. E028 signature integration
// ===================================================================

export function requestE028Signature(
  analysisId: string,
  body: RequestE028SignatureBody,
): Promise<RequestE028SignatureResponse> {
  return api<RequestE028SignatureResponse>(
    `${BASE}/analysis/${analysisId}/report-e028/request-signature`,
    { method: "POST", json: body },
  );
}

export function getE028SignatureStatus(
  analysisId: string,
): Promise<E028SignatureStatusResponse> {
  return api<E028SignatureStatusResponse>(
    `${BASE}/analysis/${analysisId}/report-e028/signature-status`,
  );
}


// ════════════════════════════════════════════════════════════════════
// 9. Cliente in-portal endpoints (SAN-E v3.MB-5.4 · review-only · Q5.3)
// ════════════════════════════════════════════════════════════════════

import { clientApi } from "@/lib/client-portal-api";


export type AssetReviewStatus =
  | "pendiente_revision"
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";

export type AssetReviewAction =
  | "revisada_ok"
  | "con_pregunta"
  | "suggest_change";


export interface MageritClientSummary {
  project_id: string;
  analysis_id: string | null;
  analysis_name: string | null;
  analysis_status: string | null;
  // Assets section
  total_assets: number;
  assets_by_type: Record<string, number>;
  reviewed_count: number;
  pending_review_count: number;
  questions_count: number;
  suggestions_count: number;
  completion_percentage: number;
  // Risks section (sub-atom 5.4.B)
  total_risks: number;
  risks_by_severity: Record<string, number>;
  risks_reviewed_count: number;
  risks_pending_review_count: number;
  risks_questions_count: number;
  risks_suggestions_count: number;
  risks_completion_percentage: number;
  // Combined readiness
  ready_for_validation_sign: boolean;
  last_signed_at: string | null;
}


export interface MageritAssetClientView {
  id: string;
  analysis_id: string;
  code: string;
  name: string;
  asset_type_code: string;
  description: string | null;
  owner: string | null;

  // Valoración DICAT (admin · cliente VE · NO edit per Q5.3)
  value_d: number | null;
  value_i: number | null;
  value_c: number | null;
  value_a: number | null;
  value_t: number | null;

  // Valores acumulados (post-propagación dependencias)
  accumulated_d: number | null;
  accumulated_i: number | null;
  accumulated_c: number | null;
  accumulated_a: number | null;
  accumulated_t: number | null;

  // Cliente review state
  client_review_status: AssetReviewStatus | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;
}


/** GET /api/v1/portal/magerit/projects/{id}/summary · cliente summary. */
export async function getMageritClientSummary(
  projectId: string,
): Promise<MageritClientSummary> {
  return clientApi<MageritClientSummary>(
    `/portal/magerit/projects/${projectId}/summary`,
  );
}


/** GET /api/v1/portal/magerit/projects/{id}/assets · list assets richer. */
export async function listMageritClientAssets(
  projectId: string,
  filters?: {
    asset_type?: string;
    review_status?: AssetReviewStatus;
  },
): Promise<MageritAssetClientView[]> {
  const params = new URLSearchParams();
  if (filters?.asset_type) params.set("asset_type", filters.asset_type);
  if (filters?.review_status)
    params.set("review_status", filters.review_status);
  const qs = params.toString();
  const path =
    `/portal/magerit/projects/${projectId}/assets${qs ? `?${qs}` : ""}`;
  return clientApi<MageritAssetClientView[]>(path);
}


/** GET /api/v1/portal/magerit/assets/{id} · asset detail. */
export async function getMageritClientAssetDetail(
  assetId: string,
): Promise<MageritAssetClientView> {
  return clientApi<MageritAssetClientView>(
    `/portal/magerit/assets/${assetId}`,
  );
}


/** POST /api/v1/portal/magerit/assets/{id}/review · cliente review action. */
export async function reviewMageritClientAsset(
  assetId: string,
  action: AssetReviewAction,
  note?: string,
): Promise<MageritAssetClientView> {
  return clientApi<MageritAssetClientView>(
    `/portal/magerit/assets/${assetId}/review`,
    { method: "POST", json: { action, note: note ?? null } },
  );
}


// ════════════════════════════════════════════════════════════════════
// Risks sub-section (sub-atom 5.4.B)
// ════════════════════════════════════════════════════════════════════


export type MageritSeverity = "baja" | "media" | "alta" | "critica";


export interface MageritRiskClientView {
  id: string;
  analysis_id: string;
  asset_id: string;
  asset_code: string;
  asset_name: string;
  asset_type_code: string;

  threat_code: string;
  threat_name: string;
  threat_group_code: string;
  threat_description: string | null;
  affected_dimensions: string[] | null;

  // Análisis MAGERIT
  probability: "MB" | "B" | "M" | "A" | "MA";
  degradation_d: number | null;
  degradation_i: number | null;
  degradation_c: number | null;
  degradation_a: number | null;
  degradation_t: number | null;
  max_degradation: number;
  severity: MageritSeverity;

  // Cliente review
  client_review_status: AssetReviewStatus | null;
  client_review_note: string | null;
  client_reviewed_at: string | null;

  last_modified_at: string | null;
}


export async function listMageritClientRisks(
  projectId: string,
  filters?: {
    severity?: MageritSeverity;
    review_status?: AssetReviewStatus;
  },
): Promise<MageritRiskClientView[]> {
  const params = new URLSearchParams();
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.review_status)
    params.set("review_status", filters.review_status);
  const qs = params.toString();
  const path =
    `/portal/magerit/projects/${projectId}/risks${qs ? `?${qs}` : ""}`;
  return clientApi<MageritRiskClientView[]>(path);
}


export async function reviewMageritClientRisk(
  riskId: string,
  action: AssetReviewAction,
  note?: string,
): Promise<MageritRiskClientView> {
  return clientApi<MageritRiskClientView>(
    `/portal/magerit/risks/${riskId}/review`,
    { method: "POST", json: { action, note: note ?? null } },
  );
}


// ════════════════════════════════════════════════════════════════════
// Document hash (sub-atom 5.4.C · SigningIntent pre-firma)
// ════════════════════════════════════════════════════════════════════


export interface MageritDocumentHashResponse {
  project_id: string;
  analysis_id: string | null;
  document_hash_sha256: string;
  canonical_length: number;
  assets_count: number;
  risks_count: number;
  last_modified_at: string | null;
  ready_for_signing: boolean;
}


export async function getMageritClientDocumentHash(
  projectId: string,
): Promise<MageritDocumentHashResponse> {
  return clientApi<MageritDocumentHashResponse>(
    `/portal/magerit/projects/${projectId}/document-hash`,
  );
}
