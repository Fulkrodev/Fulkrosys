"use client";

/**
 * Admin API golden eval runs · sub-atom 1.E.1.B.3.E.
 *
 * Endpoints backend (m_observability/golden_eval_runs_api):
 *   GET  /api/v1/admin/observability/golden-eval/datasets
 *   POST /api/v1/admin/observability/golden-eval/run
 *   GET  /api/v1/admin/observability/golden-eval/runs?agent_name&days&limit
 *   GET  /api/v1/admin/observability/golden-eval/runs/{run_id}
 *
 * Skeleton phase (B.3.D Path C-light): entries skipped si capability
 * pending build (DeliverableTextAuditor en Future-1.E.1.dossier-pack-10docs).
 * UI muestra estado "capability_pending_build" empíricamente visible.
 */

import { api } from "@/lib/api";

export type GoldenEvalRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export type GoldenEvalSeverity = "ok" | "warn" | "alert";

export interface AvailableDataset {
  agent_name: string;
  version: string;
}

export interface GoldenEvalRunDetail {
  id: string;
  agent_name: string;
  dataset_version: string;
  triggered_by_user_id: string | null;
  triggered_at: string;
  completed_at: string | null;
  status: GoldenEvalRunStatus;
  regression_score: number | null;
  severity: GoldenEvalSeverity | null;
  entries_in_dataset: number;
  entries_evaluated: number;
  entries_passed: number;
  entries_failed: number;
  failed_entry_ids: string[] | null;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
}

export interface GoldenEvalRunsListResponse {
  days: number;
  total: number;
  items: GoldenEvalRunDetail[];
}

export interface TriggerEvalRunPayload {
  agent_name: string;
  version?: string;
  sync_execute?: boolean;
}

export async function listAvailableDatasets(): Promise<AvailableDataset[]> {
  const resp = await api<{ items: AvailableDataset[] }>(
    "/api/v1/admin/observability/golden-eval/datasets",
  );
  return resp.items;
}

export async function triggerEvalRun(
  payload: TriggerEvalRunPayload,
): Promise<GoldenEvalRunDetail> {
  return api<GoldenEvalRunDetail>(
    "/api/v1/admin/observability/golden-eval/run",
    {
      json: {
        agent_name: payload.agent_name,
        version: payload.version ?? "v1",
        sync_execute: payload.sync_execute ?? true,
      },
    },
  );
}

export async function listEvalRuns(
  agentName: string | null = null,
  days: number = 30,
  limit: number = 50,
): Promise<GoldenEvalRunsListResponse> {
  const params = new URLSearchParams();
  if (agentName) params.set("agent_name", agentName);
  params.set("days", String(days));
  params.set("limit", String(limit));
  return api<GoldenEvalRunsListResponse>(
    `/api/v1/admin/observability/golden-eval/runs?${params.toString()}`,
  );
}

export async function getEvalRun(
  runId: string,
): Promise<GoldenEvalRunDetail> {
  return api<GoldenEvalRunDetail>(
    `/api/v1/admin/observability/golden-eval/runs/${runId}`,
  );
}

// Labels friendly admin-facing
export const SEVERITY_LABEL: Record<GoldenEvalSeverity, string> = {
  ok: "Verde",
  warn: "Advertencia",
  alert: "Alerta",
};

export const STATUS_LABEL: Record<GoldenEvalRunStatus, string> = {
  queued: "En cola",
  running: "Ejecutando",
  completed: "Completado",
  failed: "Falló",
};
