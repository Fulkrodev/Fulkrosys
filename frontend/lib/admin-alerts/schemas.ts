/**
 * Schemas TypeScript alertas proactivas (MB-13.4 · ADR-035).
 * Espejo de backend/app/motors/m18_communication/alert_schemas.py.
 */

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertCategory =
  | "bienal_art31"
  | "payment_overdue_aapp"
  | "client_inactivity"
  | "evidence_stale"
  | "retainer_overdue"
  | "milestone_due"
  | "workflow_blocked"
  | "audit_due"
  | "rgpd_72h"
  | "contract_milestone"
  | "renewal_due"
  | "other";

export interface AlertResponse {
  id: string;
  project_id: string;
  severity: AlertSeverity;
  category: AlertCategory;
  title: string;
  description: string | null;
  action_url: string | null;
  triggered_by: string | null;
  triggered_at: string;
  acknowledged_at: string | null;
  metadata_jsonb: Record<string, unknown> | null;
}
