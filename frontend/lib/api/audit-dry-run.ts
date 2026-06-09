/**
 * AuditDryRun API client (ADR-037 SAN-D MB-15.1).
 *
 * 3 endpoints backend (orchestrator M10 + A11 wrapper):
 *   POST /api/v1/projects/{id}/audit-dry-run/execute
 *   GET  /api/v1/projects/{id}/audit-dry-run/summary
 *   GET  /api/v1/projects/{id}/audit-dry-run/results/{result_id}
 *
 * Coste compute: 1 batch determinista M10 + 1 LLM call A11
 * (vs 58 LLM calls del briefing v2 literal · DEC-A11-58-LLM-CALLS
 * ADR-037 Deferrables).
 */
import { api } from "@/lib/api";

export type AuditEvaluacion =
  | "conforme"
  | "no_conforme_mayor"
  | "no_conforme_menor"
  | "observacion"
  | "no_aplica";

export interface M10FindingSummary {
  measure_code: string;
  measure_name?: string | null;
  evaluacion: AuditEvaluacion;
  nivel_madurez: string;
  contradiccion_detectada: boolean;
}

export interface M10Summary {
  run_id: string;
  score_global: number;
  nivel_madurez_global: string;
  conformes: number;
  no_conformes_mayores: number;
  no_conformes_menores: number;
  observaciones: number;
  no_aplica: number;
  contradicciones_count: number;
  findings: M10FindingSummary[];
}

export interface DryRunResult {
  id: string;
  project_id: string;
  executed_at: string;
  m10_run_id?: string | null;
  category_at_execution: "BASICA" | "MEDIA" | "ALTA";
  archetype_at_execution?: string | null;
  total_questions: number;
  questions_with_evidence: number;
  overall_readiness_score: number;
  gaps_detected: number;
  critical_gaps: number;
  execution_time_ms?: number | null;
  m10_summary?: M10Summary | null;
  a11_payload?: Record<string, unknown> | null;
  model_used?: string | null;
}

export interface DryRunHistoryEntry {
  id: string;
  executed_at: string;
  score: number;
  gaps: number;
  critical_gaps: number;
}

export interface DryRunSummary {
  last_executed_at?: string | null;
  overall_readiness_score: number;
  gaps_detected: number;
  critical_gaps: number;
  history: DryRunHistoryEntry[];
}

export const auditDryRunApi = {
  execute: (projectId: string): Promise<DryRunResult> =>
    api<DryRunResult>(
      `/api/v1/projects/${projectId}/audit-dry-run/execute`,
      { method: "POST" },
    ),

  getSummary: (projectId: string): Promise<DryRunSummary> =>
    api<DryRunSummary>(`/api/v1/projects/${projectId}/audit-dry-run/summary`),

  getResult: (projectId: string, resultId: string): Promise<DryRunResult> =>
    api<DryRunResult>(
      `/api/v1/projects/${projectId}/audit-dry-run/results/${resultId}`,
    ),
};
