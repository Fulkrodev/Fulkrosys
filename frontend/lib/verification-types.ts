/**
 * Types para K.17 — Verificación Técnica (Motor 8 v5.1).
 *
 * 1:1 con los schemas Pydantic de backend/app/motors/m08_verification/schemas.py.
 * Si el backend cambia, actualiza aquí antes que en los hooks o componentes.
 */

export type VerificationCategory = "BASICO" | "MEDIO" | "ALTO";
export type VerificationMode =
  | "internal"
  | "external_handoff"
  | "external_ingest_pdf"
  | "external_ingest_form";
export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type FindingStatus =
  | "open"
  | "remediated"
  | "accepted_risk"
  | "false_positive"
  | "needs_review";
export type ZfpClassification =
  | "confirmed"
  | "probable"
  | "needs_review"
  | "rejected";
export type HeatmapStatus =
  | "compliant"
  | "partial"
  | "non_compliant"
  | "not_verified";
export type Trend = "mejorando" | "estable" | "empeorando";

// ─── Run ─────────────────────────────────────────────────────────────

export interface RunSummary {
  id: string;
  project_id: string;
  category: VerificationCategory;
  mode: VerificationMode;
  status: string;
  scheduled_start: string | null;
  completed_at: string | null;
  total_findings: number;
  confirmed_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  security_score: number | null;
  delta_new: number;
  delta_resolved: number;
  delta_persistent: number;
  created_at: string;
}

export interface RunDetail extends RunSummary {
  scope_jsonb: ScopeJson;
  scope_derived_from: Record<string, unknown> | null;
  tools_used: string[];
  phase1_started_at: string | null;
  phase1_completed_at: string | null;
  phase2_started_at: string | null;
  phase2_completed_at: string | null;
  phase3_started_at: string | null;
  authorized_by: string | null;
  authorization_signed_at: string | null;
  previous_run_id: string | null;
}

export interface ScopeJson {
  category?: string;
  targets?: string[];
  web_apps?: string[];
  ssh_accessible?: string[];
  cloud_accounts?: Array<Record<string, unknown>>;
  exclusions?: string[];
  crown_jewels?: Array<Record<string, unknown>>;
  scan_window?: string;
  totals?: Record<string, number>;
  attack_chain?: Array<Record<string, unknown>>;
}

export interface RunCreateBody {
  category: VerificationCategory;
  mode?: VerificationMode;
  schedule_now?: boolean;
  tools_config?: Record<string, unknown>;
}

// ─── Findings ────────────────────────────────────────────────────────

export interface FindingSummary {
  id: string;
  run_id: string;
  title: string;
  severity: Severity;
  cvss_score: number | null;
  cve_id: string | null;
  affected_host: string;
  affected_port: number | null;
  confidence_score: number;
  zfp_gate5_classification: ZfpClassification;
  ens_primary_measure: string | null;
  status: FindingStatus;
  remediation_priority: number | null;
}

export interface FindingPatchBody {
  status?: FindingStatus;
  false_positive_reason?: string;
  accepted_risk_justification?: string;
  accepted_risk_approved_by?: string;
}

export interface RetestRequestBody {
  triggered_by?: "client_portal" | "marcos" | "scheduled";
  retest_type?: "ssl" | "cve" | "web" | "hardening" | "port";
}

export interface RetestResult {
  id: string;
  finding_id: string;
  retest_type: string;
  retest_command: string | null;
  result: "fixed" | "still_present" | "error" | "inconclusive" | null;
  result_detail: string | null;
  executed_at: string | null;
  finding_status_after: FindingStatus;
}

// ─── Heatmap / Score / Delta ─────────────────────────────────────────

export interface HeatmapCell {
  measure: string;
  status: HeatmapStatus;
  color: "verde" | "amarillo" | "rojo" | "gris";
  findings_count: number;
  worst_severity: Severity | null;
  findings_hashes: string[];
}

export interface HeatmapSummary {
  compliant: number;
  partial: number;
  non_compliant: number;
  not_verified: number;
  total: number;
  compliant_pct: number;
  partial_pct: number;
  non_compliant_pct: number;
  not_verified_pct: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
  summary: HeatmapSummary;
}

export interface SecurityScore {
  score: number;
  level: "excelente" | "aceptable" | "mejorable" | "critico" | "bloqueante";
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  total_penalty: number;
}

export interface ScoreResponse {
  current: SecurityScore;
  history: Array<{
    run_id: string;
    score: number | null;
    completed_at: string | null;
  }>;
}

export interface DeltaFinding {
  finding_hash: string;
  severity: Severity;
  title: string;
}

export interface SeverityChange {
  finding_hash: string;
  title: string;
  from_sev: Severity;
  to_sev: Severity;
}

export interface DeltaResponse {
  previous_run_id: string | null;
  current_run_id: string | null;
  new: DeltaFinding[];
  resolved: DeltaFinding[];
  persistent: DeltaFinding[];
  severity_changes: SeverityChange[];
  overall_trend: Trend;
  weight_previous: number;
  weight_current: number;
  totals: {
    new: number;
    resolved: number;
    persistent: number;
    severity_changes: number;
  };
}

// ─── Remediation plan ────────────────────────────────────────────────

export interface RemediationPlanItem {
  finding_id: string;
  title: string;
  severity: Severity;
  classification: ZfpClassification;
  affected_host: string;
  ens_primary_measure: string | null;
  remediation_effort: "quick_win" | "short_term" | "long_term" | null;
  remediation_summary: string;
  status: FindingStatus;
  sla: {
    severity: Severity;
    calculated_from: string;
    deadline: string;
    hours_total: number;
    hours_remaining: number;
    overdue: boolean;
  };
}

export interface RemediationPlanResponse {
  total: number;
  items: RemediationPlanItem[];
}

// ─── Handoff ─────────────────────────────────────────────────────────

export interface HandoffCreateBody {
  run_id: string;
  pentester_name: string;
  pentester_email: string;
  pentester_cert: string;
  deadline?: string;
  findings_submission_method?: "pdf" | "structured_form" | "both";
}

export interface HandoffResponse {
  handoff_id: string;
  project_id: string;
  run_id: string;
  status: string;
  package_documents: Array<{
    name: string;
    path: string;
    generated_at: string;
    hash_sha256: string;
  }>;
  pentester_name: string | null;
  created_at: string | null;
}

// ─── Reports ─────────────────────────────────────────────────────────

export interface ReportRequestBody {
  template_codigo: "E-702" | "E-703" | "E-704";
  generate_pdf?: boolean;
  sign?: boolean;
  remediation_force_offline?: boolean;
}

export interface ReportResponse {
  document_id: string;
  template_codigo: string;
  nombre: string;
  docx_path: string;
  pdf_path: string | null;
  rendered_hash: string;
  signature_ed25519: string | null;
  estado: string;
}

// ─── Kill switch ─────────────────────────────────────────────────────

export interface KillResponse {
  id: string;
  status: string;
  cancel_requested_at: string | null;
  cancel_completed_at: string | null;
}
