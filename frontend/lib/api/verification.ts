/**
 * Motor 8 v5.1 — Verificación técnica — cliente REST.
 *
 * 14 endpoints + kill switch. Todos hablan con el backend real,
 * sin mocks. Usa el wrapper `api()` que añade CSRF + credentials.
 */
import { api } from "@/lib/api";
import type {
  DeltaResponse,
  FindingPatchBody,
  FindingSummary,
  HandoffCreateBody,
  HandoffResponse,
  HeatmapResponse,
  KillResponse,
  RemediationPlanResponse,
  ReportRequestBody,
  ReportResponse,
  RetestRequestBody,
  RetestResult,
  RunCreateBody,
  RunDetail,
  RunSummary,
  ScoreResponse,
} from "@/lib/verification-types";

const BASE = "/api/v1";

// ─── Runs ─────────────────────────────────────────────────────────────

export async function createVerificationRun(
  projectId: string,
  body: RunCreateBody,
): Promise<RunSummary> {
  return api<RunSummary>(`${BASE}/projects/${projectId}/verification/run`, {
    json: body,
  });
}

export async function listVerificationRuns(
  projectId: string,
  status?: string,
): Promise<{ runs: RunSummary[] }> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return api<{ runs: RunSummary[] }>(
    `${BASE}/projects/${projectId}/verification/runs${qs}`,
  );
}

export async function getVerificationRun(
  projectId: string,
  runId: string,
): Promise<RunDetail> {
  return api<RunDetail>(
    `${BASE}/projects/${projectId}/verification/runs/${runId}`,
  );
}

// ─── Findings ─────────────────────────────────────────────────────────

export interface ListFindingsFilters {
  severity?: string;
  status?: string;
  ens_measure?: string;
  classification?: string;
}

export async function listFindings(
  projectId: string,
  runId: string,
  filters: ListFindingsFilters = {},
): Promise<{ findings: FindingSummary[] }> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v) qs.set(k, v);
  }
  const q = qs.toString();
  return api<{ findings: FindingSummary[] }>(
    `${BASE}/projects/${projectId}/verification/runs/${runId}/findings${q ? `?${q}` : ""}`,
  );
}

export async function patchFinding(
  projectId: string,
  findingId: string,
  body: FindingPatchBody,
): Promise<FindingSummary> {
  return api<FindingSummary>(
    `${BASE}/projects/${projectId}/verification/findings/${findingId}`,
    { method: "PATCH", json: body },
  );
}

export interface EnsMeasureInput {
  measure: string;
  title: string;
  method?: string;
  citation?: string;
  confidence?: number;
}

export async function patchFindingMapping(
  projectId: string,
  findingId: string,
  body: {
    ens_measures: EnsMeasureInput[];
    ens_primary_measure?: string | null;
  },
): Promise<FindingSummary> {
  return api<FindingSummary>(
    `${BASE}/projects/${projectId}/verification/findings/${findingId}/mapping`,
    { method: "PATCH", json: body },
  );
}

// ─── Remediation ──────────────────────────────────────────────────────

export async function requestRetest(
  projectId: string,
  findingId: string,
  body: RetestRequestBody = {},
): Promise<RetestResult> {
  return api<RetestResult>(
    `${BASE}/projects/${projectId}/verification/findings/${findingId}/retest`,
    { json: body },
  );
}

export async function getRemediationPlan(
  projectId: string,
): Promise<RemediationPlanResponse> {
  return api<RemediationPlanResponse>(
    `${BASE}/projects/${projectId}/verification/remediation-plan`,
  );
}

// ─── Handoff ──────────────────────────────────────────────────────────

export async function createHandoff(
  projectId: string,
  body: HandoffCreateBody,
): Promise<HandoffResponse> {
  return api<HandoffResponse>(
    `${BASE}/projects/${projectId}/verification/handoff`,
    { json: body },
  );
}

export interface IngestRequestBody {
  run_id: string;
  source: "pdf" | "structured_form";
  pdf_base64?: string;
  original_pdf_path?: string;
  findings?: Array<{
    title: string;
    description: string;
    severity: string;
    affected_host: string;
    affected_port?: number;
    cve_id?: string;
    cvss_score?: number;
  }>;
}

export async function ingestExternalFindings(
  projectId: string,
  body: IngestRequestBody,
): Promise<{
  run_id: string;
  source: string;
  findings_ingested: number;
  finding_ids: string[];
}> {
  return api(
    `${BASE}/projects/${projectId}/verification/ingest`,
    { json: body },
  );
}

// ─── Reports ──────────────────────────────────────────────────────────

export async function generateReport(
  projectId: string,
  runId: string,
  body: ReportRequestBody,
): Promise<ReportResponse> {
  return api<ReportResponse>(
    `${BASE}/projects/${projectId}/verification/runs/${runId}/report`,
    { json: body },
  );
}

export async function getHeatmap(
  projectId: string,
): Promise<HeatmapResponse> {
  return api<HeatmapResponse>(
    `${BASE}/projects/${projectId}/verification/heatmap`,
  );
}

export async function getScore(projectId: string): Promise<ScoreResponse> {
  return api<ScoreResponse>(
    `${BASE}/projects/${projectId}/verification/score`,
  );
}

export async function getDelta(projectId: string): Promise<DeltaResponse> {
  return api<DeltaResponse>(
    `${BASE}/projects/${projectId}/verification/delta`,
  );
}

// ─── K.5 integration (findings by measure) ───────────────────────────

export interface FindingsByMeasureResponse {
  measure_code: string;
  findings: import("@/lib/verification-types").FindingSummary[];
  counts: {
    total: number;
    open: number;
    remediated: number;
    critical_or_high_open: number;
  };
  reports: Array<{
    document_id: string;
    template_codigo: string;
    nombre: string;
    docx_path: string | null;
    pdf_path: string | null;
    rendered_hash: string | null;
    generated_at: string | null;
  }>;
  last_verified: string | null;
}

export async function getFindingsByMeasure(
  projectId: string,
  measureCode: string,
): Promise<FindingsByMeasureResponse> {
  return api<FindingsByMeasureResponse>(
    `${BASE}/projects/${projectId}/verification/by-measure/${encodeURIComponent(measureCode)}`,
  );
}

// ─── Kill switch ──────────────────────────────────────────────────────

export async function killRun(
  projectId: string,
  runId: string,
): Promise<KillResponse> {
  return api<KillResponse>(
    `${BASE}/projects/${projectId}/verification/runs/${runId}/kill`,
    { json: {} },
  );
}
