/**
 * Motor 21 - Organizational Diagnosis API client.
 *
 * 17 endpoints reales (zero-mock):
 *   - 10 endpoints orquestacion: run/latest/runs/maturity/stakeholders/compliance,
 *     generate-report, generate-docx, download-docx, quick-wins
 *   - 6 endpoints CRUD: stakeholders/processes/legal-obligations (POST + GET)
 *   - 1 endpoint exporter M21 -> M2 MAGERIT
 *
 * Tipos espejo de los Pydantic schemas y serializers en
 * backend/app/motors/m21_diagnosis/api.py. UI types
 * (DiagnosisData, Stakeholder, BusinessProcess, etc.) viven en
 * @/lib/project-types; aqui mantenemos los DTO server-side.
 *
 * Usa api() wrapper con CSRF + credentials.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/diagnosis";

// ===================================================================
// Tipos compartidos (espejo Pydantic backend)
// ===================================================================

export type DiagnosisActitud =
  | "sponsor"
  | "neutral"
  | "blocker"
  | string;

export type DiagnosisCriticidad = "alta" | "media" | "baja" | string;

// ----- Run / Latest / Runs -----

export interface RunDiagnosisBody {
  sector: string;
  triggered_by?: string;
  confidential_notes?: string | null;
}

export interface DiagnosisMaturityScoring {
  level?: string;
  score_pct?: number;
  [k: string]: unknown;
}

export interface DiagnosisRunOut {
  run_id?: string;
  project_id?: string;
  sector?: string | null;
  triggered_at?: string;
  triggered_by?: string;
  status?: string;
  maturity_scoring?: DiagnosisMaturityScoring | null;
  stakeholder_analysis?: Record<string, unknown> | null;
  compliance_detection?: Record<string, unknown> | null;
  process_analysis?: Record<string, unknown> | null;
  cross_compliance?: Record<string, unknown> | null;
  report_data?: Record<string, unknown> | null;
  report_docx_path?: string | null;
  [k: string]: unknown;
}

export interface DiagnosisRunsListItem {
  id: string;
  status: string;
  triggered_at: string;
  triggered_by: string;
  sector: string | null;
}

// ----- Quick Wins -----

export interface QuickWinItem {
  id?: string;
  title?: string;
  description?: string;
  impact?: string;
  effort?: string;
  [k: string]: unknown;
}

export interface QuickWinsResponse {
  quick_wins: QuickWinItem[];
  total: number;
}

// ----- Report DOCX -----

export interface DocxGenerateResponse {
  docx_path: string;
  status: string;
}

// ----- CRUD bodies (Sprint C4) -----

export interface StakeholderBody {
  nombre: string;
  cargo?: string | null;
  departamento?: string | null;
  poder?: number | null;
  interes?: number | null;
  actitud?: DiagnosisActitud | null;
  email?: string | null;
  telefono?: string | null;
  notas_confidenciales?: string | null;
}

export interface StakeholderOut {
  id: string;
  project_id: string;
  nombre: string;
  cargo: string | null;
  departamento: string | null;
  poder: number | null;
  interes: number | null;
  actitud: string | null;
  email: string | null;
}

export interface ProcessBody {
  nombre: string;
  descripcion?: string | null;
  criticidad?: DiagnosisCriticidad | null;
  propietario?: string | null;
  bpmn_mermaid?: string | null;
  rto_horas?: number | null;
  rpo_horas?: number | null;
}

export interface ProcessOut {
  id: string;
  project_id: string;
  nombre: string;
  descripcion: string | null;
  criticidad: string | null;
  propietario: string | null;
  rto_horas: number | null;
  rpo_horas: number | null;
}

export interface LegalObligationBody {
  normativa: string;
  articulo?: string | null;
  alcance?: string | null;
  impacto_ens?: string | null;
  estado?: string | null;
  notas?: string | null;
}

export interface LegalObligationOut {
  id: string;
  project_id: string;
  normativa: string;
  articulo: string | null;
  alcance: string | null;
  impacto_ens: string | null;
  estado: string | null;
}

// ----- MAGERIT export -----

export interface MageritExportResponse {
  exported: number;
  message?: string;
  analysis_id?: string;
  processes_source?: number;
}

// ===================================================================
// Endpoints - Orquestacion (10)
// ===================================================================

/** POST /api/v1/diagnosis/projects/{id}/run */
export function runDiagnosis(
  projectId: string,
  body: RunDiagnosisBody,
): Promise<DiagnosisRunOut> {
  return api(`${BASE}/projects/${projectId}/run`, {
    method: "POST",
    json: body,
  });
}

/** GET /api/v1/diagnosis/projects/{id}/latest?include_confidential=... */
export function getLatestDiagnosis(
  projectId: string,
  includeConfidential = false,
): Promise<DiagnosisRunOut> {
  const qs = includeConfidential ? "?include_confidential=true" : "";
  return api(`${BASE}/projects/${projectId}/latest${qs}`);
}

/** GET /api/v1/diagnosis/projects/{id}/runs */
export function listDiagnosisRuns(
  projectId: string,
): Promise<DiagnosisRunsListItem[] | { runs: DiagnosisRunsListItem[] }> {
  return api(`${BASE}/projects/${projectId}/runs`);
}

/** GET /api/v1/diagnosis/projects/{id}/maturity */
export function getDiagnosisMaturity(
  projectId: string,
): Promise<DiagnosisMaturityScoring> {
  return api(`${BASE}/projects/${projectId}/maturity`);
}

/** GET /api/v1/diagnosis/projects/{id}/stakeholders (snapshot run) */
export function getDiagnosisStakeholdersSnapshot(
  projectId: string,
): Promise<Record<string, unknown>> {
  return api(`${BASE}/projects/${projectId}/stakeholders`);
}

/** GET /api/v1/diagnosis/projects/{id}/compliance */
export function getDiagnosisCompliance(
  projectId: string,
): Promise<Record<string, unknown>> {
  return api(`${BASE}/projects/${projectId}/compliance`);
}

/** POST /api/v1/diagnosis/projects/{id}/runs/{run_id}/generate-report */
export function generateDiagnosisReport(
  projectId: string,
  runId: string,
): Promise<Record<string, unknown>> {
  return api(
    `${BASE}/projects/${projectId}/runs/${runId}/generate-report`,
    { method: "POST" },
  );
}

/** POST /api/v1/diagnosis/projects/{id}/runs/{run_id}/generate-docx */
export function generateDiagnosisDocx(
  projectId: string,
  runId: string,
): Promise<DocxGenerateResponse> {
  return api(
    `${BASE}/projects/${projectId}/runs/${runId}/generate-docx`,
    { method: "POST" },
  );
}

/**
 * GET /api/v1/diagnosis/projects/{id}/runs/{run_id}/download-docx → Blob (.docx).
 * Espejo de generatePdaDocx: el wrapper api() parsea JSON y no sirve para
 * binarios, así que se hace fetch crudo con credentials. GET → sin CSRF.
 */
export async function downloadDiagnosisDocx(
  projectId: string,
  runId: string,
): Promise<Blob> {
  const response = await fetch(
    `${BASE}/projects/${projectId}/runs/${runId}/download-docx`,
    { method: "GET", credentials: "include" },
  );
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        detail = String((payload as { detail: unknown }).detail);
      }
    } catch {
      // respuesta no-JSON (p.ej. binario o vacío) · conservar statusText
    }
    throw new Error(detail);
  }
  return response.blob();
}

/** GET /api/v1/diagnosis/projects/{id}/runs/{run_id}/quick-wins */
export function getDiagnosisQuickWins(
  projectId: string,
  runId: string,
): Promise<QuickWinsResponse> {
  return api(`${BASE}/projects/${projectId}/runs/${runId}/quick-wins`);
}

// ===================================================================
// Endpoints - CRUD (Sprint C4) (6)
// ===================================================================

/** POST /api/v1/diagnosis/projects/{id}/diagnosis/stakeholders */
export function createDiagnosisStakeholder(
  projectId: string,
  body: StakeholderBody,
): Promise<StakeholderOut> {
  return api(
    `${BASE}/projects/${projectId}/diagnosis/stakeholders`,
    { method: "POST", json: body },
  );
}

/** GET /api/v1/diagnosis/projects/{id}/diagnosis/stakeholders */
export function listDiagnosisStakeholders(
  projectId: string,
): Promise<{ stakeholders: StakeholderOut[] }> {
  return api(`${BASE}/projects/${projectId}/diagnosis/stakeholders`);
}

/** POST /api/v1/diagnosis/projects/{id}/diagnosis/processes */
export function createDiagnosisProcess(
  projectId: string,
  body: ProcessBody,
): Promise<ProcessOut> {
  return api(
    `${BASE}/projects/${projectId}/diagnosis/processes`,
    { method: "POST", json: body },
  );
}

/** GET /api/v1/diagnosis/projects/{id}/diagnosis/processes */
export function listDiagnosisProcesses(
  projectId: string,
): Promise<{ processes: ProcessOut[] }> {
  return api(`${BASE}/projects/${projectId}/diagnosis/processes`);
}

/** POST /api/v1/diagnosis/projects/{id}/diagnosis/legal-obligations */
export function createDiagnosisLegalObligation(
  projectId: string,
  body: LegalObligationBody,
): Promise<LegalObligationOut> {
  return api(
    `${BASE}/projects/${projectId}/diagnosis/legal-obligations`,
    { method: "POST", json: body },
  );
}

/** GET /api/v1/diagnosis/projects/{id}/diagnosis/legal-obligations */
export function listDiagnosisLegalObligations(
  projectId: string,
): Promise<{ legal_obligations: LegalObligationOut[] }> {
  return api(`${BASE}/projects/${projectId}/diagnosis/legal-obligations`);
}

// ===================================================================
// Exporter M21 -> M2 MAGERIT (1)
// ===================================================================

/** POST /api/v1/diagnosis/projects/{id}/diagnosis/export-to-magerit?magerit_analysis_id=... */
export function exportDiagnosisToMagerit(
  projectId: string,
  mageritAnalysisId: string,
): Promise<MageritExportResponse> {
  const qs = `?magerit_analysis_id=${encodeURIComponent(mageritAnalysisId)}`;
  return api(
    `${BASE}/projects/${projectId}/diagnosis/export-to-magerit${qs}`,
    { method: "POST" },
  );
}
