/**
 * API client for /admin/compliance/norma-reports (mini-atom 3).
 *
 * Mirrors backend/app/motors/m_compliance_monitor/norma_reports_api.py.
 */
import { api } from "@/lib/api";

export interface NormaSummary {
  norma_key: string;
  norma_name: string;
  regulatory_basis_url: string;
  frequency: string;
  priority: string;
  checks_owned: string[];
  latest_score: number | null;
  latest_status: "green" | "yellow" | "red" | "unknown" | null;
  latest_generated_at: string | null;
}

export interface NormaReport {
  id: string;
  norma_key: string;
  norma_name: string;
  period_start: string;
  period_end: string;
  compliance_score: number;
  status: "green" | "yellow" | "red" | "unknown";
  checks_total: number;
  checks_passed: number;
  checks_warning: number;
  checks_failed: number;
  generated_at: string;
  storage_path_dev: string | null;
  storage_path_prod: string | null;
  email_sent_at: string | null;
  reviewed_by_marcos_at: string | null;
  reviewed_marcos_notes: string | null;
}

export interface NormaReportDetail extends NormaReport {
  report_md_content: string;
  report_json_content: Record<string, unknown>;
}

const BASE = "/api/v1/admin/compliance/norma-reports";

export async function listNormas(): Promise<NormaSummary[]> {
  return api<NormaSummary[]>(BASE);
}

export async function getNormaHistory(
  normaKey: string,
  limit = 24,
): Promise<NormaReport[]> {
  return api<NormaReport[]>(`${BASE}/${normaKey}?limit=${limit}`);
}

export async function getNormaLatest(normaKey: string): Promise<NormaReportDetail> {
  return api<NormaReportDetail>(`${BASE}/${normaKey}/latest`);
}

export async function runNormaReport(normaKey: string): Promise<NormaReportDetail> {
  return api<NormaReportDetail>(`${BASE}/${normaKey}/run`, { method: "POST" });
}

export async function markReportReviewed(
  reportId: string,
  notes: string | null,
): Promise<NormaReport> {
  return api<NormaReport>(`${BASE}/reviewed/${reportId}`, {
    method: "POST",
    json: { notes },
  });
}
