/**
 * Schemas TypeScript dashboard agregado admin (MB-13.1 · ADR-035).
 *
 * Espejo de backend/app/motors/m21_diagnosis/dashboard_schemas.py.
 * Endpoint: GET /api/v1/projects/{project_id}/dashboard.
 */

export type AlertSeverity = "info" | "warning" | "critical";

export interface NextActionItem {
  action_id: string;
  label: string;
  motor: string;
  cta: string;
  action_url: string;
  estimated_minutes: number;
  priority: number;
  urgent: boolean;
  blocking: boolean;
}

export interface ActiveAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  description: string;
  action_url: string;
  triggered_at: string;
}

export interface DashboardData {
  project_id: string;
  project_name: string;
  category: string;
  archetype: string | null;
  current_phase: string;
  current_phase_label: string;
  phase_index: number;
  phase_total: number;
  next_actions: NextActionItem[];
  readiness_score: number;
  active_alerts: ActiveAlert[];
  active_alerts_count: number;
  estimated_days_to_certification: number | null;
  blocking_issues: string[];
  last_updated: string;
}
