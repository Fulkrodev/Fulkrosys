/**
 * SIEM API client (FRENTE N) · consola admin de eventos de seguridad.
 * Endpoints: GET /api/v1/admin/siem/overview · /events (require_owner · read-only).
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/admin/siem";

export type SiemSeverity = "critical" | "high" | "medium" | "low" | "info";

export interface SiemEvent {
  source: "pentest" | "incident" | "escalation" | "compliance";
  event_type: string;
  severity: SiemSeverity;
  occurred_at: string | null;
  project_id: string | null;
  title: string;
  ref_id: string | null;
  resolved: boolean;
  details: Record<string, unknown>;
}

export interface SiemCorrelation {
  rule_id: string;
  severity: SiemSeverity;
  title: string;
  description: string;
  event_count: number;
  project_id: string | null;
}

export interface SiemOverview {
  total_events: number;
  active_events: number;
  by_severity: Record<SiemSeverity, number>;
  by_source: Record<string, number>;
  correlations: SiemCorrelation[];
  correlation_count: number;
  events: SiemEvent[];
}

export function getSiemOverview(projectId?: string): Promise<SiemOverview> {
  const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api<SiemOverview>(`${BASE}/overview${qs}`);
}
