/**
 * Simulacro Pre-ENAC API client · Sesión 3B-2B.10 Phase 10.4 (2026-05-27).
 *
 * 2 endpoints backend (orchestrator delgado M09 + reuse 5 existing services):
 *   POST /api/v1/admin/projects/{id}/simulacro-pre-enac/execute
 *   GET  /api/v1/admin/projects/{id}/simulacro-pre-enac/last-report
 *
 * Composes: AuditDryRun + DdA gap matrix + workflow + audit_log integrity +
 *           corrective loops + signed PDF (reuse draft_report_generator C4).
 */
import { api, ApiError } from "@/lib/api";

export interface SimulacroLoopMetadata {
  loop_id: string;
  gap_id?: string | null;
  severity?: string | null;
}

export interface SimulacroReport {
  project_id: string;
  executed_at: string;
  overall_readiness_score: number;
  total_gaps: number;
  critical_gaps: number;
  high_gaps: number;
  coverage_pct: number;
  current_phase: string;
  integrity_ok: boolean;
  integrity_first_bad_seq: number | null;
  corrective_loops_opened: number;
  pdf_sha256: string;
  signature_hex: string;
  signed_at: string;
  pdf_size_bytes: number;
  loops_metadata: SimulacroLoopMetadata[];
}

export const simulacroPreEnacApi = {
  execute: (projectId: string): Promise<SimulacroReport> =>
    api<SimulacroReport>(
      `/api/v1/admin/projects/${projectId}/simulacro-pre-enac/execute`,
      { method: "POST" },
    ),
  getLastReport: async (projectId: string): Promise<SimulacroReport | null> => {
    try {
      return await api<SimulacroReport>(
        `/api/v1/admin/projects/${projectId}/simulacro-pre-enac/last-report`,
      );
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },
};
