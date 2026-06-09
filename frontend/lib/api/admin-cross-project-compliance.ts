/**
 * API client admin · Cross-Project Compliance aggregator (Bloque 4 Phase B).
 *
 * Endpoint: GET /api/v1/admin/cross-project-compliance
 * Auth: require_owner
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/admin/cross-project-compliance";

export type AdminHealthIndicator = "ok" | "warning" | "critical" | "unknown";

export interface ProjectComplianceRow {
  project_id: string;
  project_name: string;
  client_id: string;
  client_name: string;
  lifecycle_state: string | null;
  categoria_objetivo: string | null;
  overall_health: AdminHealthIndicator;
  conformity_status: AdminHealthIndicator;
  remediations_pending: number;
  tasks_pending: number;
  evidences_missing: number;
  gaps_critical_open: number;
  last_activity_at: string | null;
}

export interface CrossProjectComplianceResponse {
  generated_at: string;
  total_projects: number;
  counts_by_health: Record<AdminHealthIndicator, number>;
  projects: ProjectComplianceRow[];
}

export const ADMIN_HEALTH_LABELS: Record<AdminHealthIndicator, string> = {
  ok: "OK",
  warning: "Atención",
  critical: "Crítico",
  unknown: "Sin datos",
};

export const ADMIN_HEALTH_VARIANTS: Record<
  AdminHealthIndicator,
  "success" | "warning" | "danger" | "outline"
> = {
  ok: "success",
  warning: "warning",
  critical: "danger",
  unknown: "outline",
};

export const adminCrossProjectComplianceApi = {
  list: (params: { only_active?: boolean } = {}) => {
    const qs = params.only_active === false ? "?only_active=false" : "";
    return api<CrossProjectComplianceResponse>(`${BASE}${qs}`);
  },
};
