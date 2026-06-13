// API admin · motor de remediación (ADR-055). Usa el wrapper `api` (base /api/v1).
import { api } from "@/lib/api";

export type RemediationTier = "safe_auto" | "guarded" | "blocked";

export interface RemediationCatalogAction {
  action_type: string;
  title: string;
  tier: RemediationTier;
  reversible: boolean;
  provider: string;
  ens_measures: string[];
  cliente_blurb: string;
  requires_write_scopes: string[];
}

export interface RemediationJob {
  id: string;
  project_id: string;
  action_type: string;
  title: string;
  tier: RemediationTier;
  status: string;
  source_kind: string;
  source_gap_id: string | null;
  connector_id: string | null;
  target_ref: string | null;
  dry_run: boolean;
  ens_measures: string[];
  authorized_at: string | null;
  error_message: string | null;
  result: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface CreateRemediationJobBody {
  action_type: string;
  source_kind?: string;
  source_gap_id?: string | null;
  connector_id?: string | null;
  target_ref?: string | null;
  params?: Record<string, unknown> | null;
  dry_run?: boolean;
}

export interface RemediationConnectorOption {
  id: string;
  provider: string;
  status: string;
}

const BASE = "/api/v1/admin/projects";

export const remediationAdminApi = {
  catalog: (projectId: string) =>
    api<{ actions: RemediationCatalogAction[] }>(
      `${BASE}/${projectId}/remediation/catalog`,
    ),

  listJobs: (projectId: string, status?: string) =>
    api<{ jobs: RemediationJob[] }>(
      `${BASE}/${projectId}/remediation/jobs` +
        (status ? `?status=${encodeURIComponent(status)}` : ""),
    ),

  getJob: (projectId: string, jobId: string) =>
    api<RemediationJob>(`${BASE}/${projectId}/remediation/jobs/${jobId}`),

  createJob: (projectId: string, body: CreateRemediationJobBody) =>
    api<RemediationJob>(`${BASE}/${projectId}/remediation/jobs`, {
      method: "POST",
      json: body,
    }),

  authorize: (projectId: string, jobId: string) =>
    api<RemediationJob>(
      `${BASE}/${projectId}/remediation/jobs/${jobId}/authorize`,
      { method: "POST", json: {} },
    ),

  execute: (projectId: string, jobId: string) =>
    api<RemediationJob>(
      `${BASE}/${projectId}/remediation/jobs/${jobId}/execute`,
      { method: "POST", json: {} },
    ),

  // Reuse endpoint de conectores cloud existente (OPS-026) para el selector.
  listConnectors: async (
    projectId: string,
  ): Promise<RemediationConnectorOption[]> => {
    const res = await api<{
      items: Array<{ id: string; provider: string; status: string }>;
    }>(`${BASE}/${projectId}/cloud-connectors`);
    return (res.items ?? []).map((c) => ({
      id: c.id,
      provider: c.provider,
      status: c.status,
    }));
  },
};
