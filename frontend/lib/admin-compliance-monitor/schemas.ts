/**
 * Types for /admin/compliance/monitor (FULKRO Self-Monitoring System).
 *
 * Mirror of backend `m_compliance_monitor.schemas`. Keep field names in
 * sync — backend is source of truth.
 */

export type CheckStatus = "green" | "yellow" | "red" | "unknown";
export type CheckSeverity = "high" | "medium" | "low";
export type CheckFrequency = "daily" | "weekly" | "monthly" | "quarterly";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface MonitorStatus {
  overall: CheckStatus;
  green: number;
  yellow: number;
  red: number;
  unknown: number;
  total: number;
  open_alerts: number;
  last_run_at: string | null;
  last_report_at: string | null;
}

export interface ComplianceCheck {
  id: string;
  check_name: string;
  category: string;
  frequency: CheckFrequency;
  severity_threshold: CheckSeverity;
  status: CheckStatus;
  last_run_at: string | null;
  next_run_at: string | null;
  consecutive_failures: number;
  description: string | null;
  regulatory_basis: string | null;
  last_result: {
    status: CheckStatus;
    message: string;
    severity: CheckSeverity;
    details: Record<string, unknown>;
    ran_at: string;
  } | null;
}

export interface ComplianceAlert {
  id: string;
  check_id: string;
  check_name: string;
  severity: CheckSeverity;
  status: AlertStatus;
  message: string;
  details: Record<string, unknown> | null;
  triggered_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
  auto_resolved: boolean | null;
  email_sent_at: string | null;
}

export interface ComplianceReport {
  id: string;
  report_type: string;
  period_start: string;
  period_end: string;
  summary: Record<string, number>;
  storage_mode: "desktop" | "minio" | "inline";
  storage_path: string | null;
  signed_url: string | null;
  signed_url_expires_at: string | null;
  email_sent_to: string | null;
  email_sent_at: string | null;
  generated_at: string;
}

export interface TriggerCheckResult {
  check_name: string;
  result: {
    check_name: string;
    status: CheckStatus;
    severity: CheckSeverity | null;
    message: string;
    details: Record<string, unknown>;
    ran_at: string;
  };
  alert_created: boolean;
  alert_id: string | null;
}
