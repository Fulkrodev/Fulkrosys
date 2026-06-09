/**
 * API client cliente · Compliance Summary aggregator (Bloque 4 Phase A).
 *
 * Endpoint NUEVO aggregator que combina:
 *   - M27 conformity readiness status
 *   - M04 plan adecuación completion
 *   - M07 evidencias count + pending
 *   - Cloud remediations pending (Bloque 3+5)
 *   - Tasks cliente pending action
 *
 * Endpoint: GET /api/v1/client-portal/compliance-summary
 * Auth: require_client_user (ADR-013 doble pool)
 * Scope: single-project per cliente (Audit Bloque 1 #4 cliente portal · 1 cliente ≈ 1 project)
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/client-portal/compliance-summary";

export type HealthIndicator = "ok" | "warning" | "critical" | "unknown";

export interface ComplianceArea {
  area_key: string;
  title: string;
  status: HealthIndicator;
  friendly_message: string;
  pending_count: number;
  detail_url: string | null;
}

export interface ComplianceSummaryResponse {
  project_id: string | null;
  overall_health: HealthIndicator;
  generated_at: string;
  areas: ComplianceArea[];
}

export const HEALTH_LABELS: Record<HealthIndicator, string> = {
  ok: "Al día",
  warning: "Algo a revisar",
  critical: "Necesita tu atención",
  unknown: "Pendiente de actualizar",
};

export const HEALTH_VARIANTS: Record<
  HealthIndicator,
  "success" | "warning" | "danger" | "outline"
> = {
  ok: "success",
  warning: "warning",
  critical: "danger",
  unknown: "outline",
};

export const clientComplianceSummaryApi = {
  get: () => api<ComplianceSummaryResponse>(BASE),
};
