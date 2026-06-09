/**
 * Types para los 3 portales publicos (Motor 8 v5.1 Checkpoint 3B).
 */

export type Severity = "critical" | "high" | "medium" | "low" | "info";

// ─── Remediation portal ───────────────────────────────────────────────

export interface RemediationFindingCard {
  finding_id: string;
  title: string;
  severity: Severity;
  host_port: string;
  summary_non_technical: string;
  risk_real: string;
  time_estimate: string;
  requires_restart: boolean;
  requires_maintenance_window: boolean;
  status: string;
  remediated_at: string | null;
}

export interface RemediationData {
  cliente: { razon_social: string; cif: string };
  scope: { project_id: string; scan_date: string | null };
  progress: {
    total: number;
    resolved: number;
    pending: number;
    pct: number;
  };
  severity_buckets: Record<
    "critical" | "high" | "medium" | "low",
    { pending: number; total: number }
  >;
  pending_findings: RemediationFindingCard[];
  resolved_findings: Array<{
    finding_id: string;
    title: string;
    severity: Severity;
    remediated_at: string | null;
  }>;
}

export interface RemediationGuide {
  finding_id: string;
  title: string;
  severity: Severity;
  host_port: string;
  guide: {
    resumen_no_tecnico: string;
    riesgo_real: string;
    pasos: Array<{
      paso: number;
      titulo: string;
      comando: string;
      explicacion: string;
      verificacion: string;
    }>;
    tiempo_estimado: string;
    requiere_reinicio: boolean;
    requiere_ventana_mantenimiento: boolean;
    fuente: string;
  };
}

export interface RemediationRetestResult {
  finding_id: string;
  retest_result: "fixed" | "still_present" | "error" | "inconclusive" | null;
  retest_detail: string | null;
  executed_at: string | null;
  finding_status_after: string;
  verified_at: string | null;
}

// ─── Pentester portal ─────────────────────────────────────────────────

export interface PentesterPortalData {
  cliente: { razon_social: string; cif: string };
  engagement: {
    run_id: string;
    handoff_id: string;
    category: string;
    mode: string;
    scope: {
      targets: string[];
      web_apps: string[];
      exclusions: string[];
      scan_window: string;
    };
    deadline: string | null;
    kickoff_scheduled_at: string | null;
    status: string;
    report_received_at: string | null;
    total_findings_received: number | null;
  };
  pentester: {
    name: string;
    certification: string;
    email: string;
  };
  documents: Array<{
    name: string;
    path: string;
    hash_sha256: string;
    generated_at: string;
  }>;
  vpn: {
    config_available: boolean;
    requires_otp_for_creds: boolean;
  };
  consultor_contact: {
    nombre: string;
    email: string;
    phone_emergency: string;
    procedimiento: string;
  };
}

export interface PentesterFindingInput {
  title: string;
  description: string;
  severity: Severity;
  affected_host: string;
  affected_port?: number | null;
  affected_url?: string | null;
  cve_id?: string | null;
  cvss_score?: number | null;
  cvss_vector?: string | null;
  cwe_id?: string | null;
  remediation_summary?: string | null;
}

export interface PentesterCompleteResponse {
  status: string;
  report_received_at: string | null;
}

// ─── Verify-auth portal ───────────────────────────────────────────────

export interface VerifyAuthData {
  cliente: { razon_social: string; cif: string };
  run: {
    run_id: string;
    category: string;
    mode: string;
    scheduled_start: string | null;
    scope: {
      targets: string[];
      web_apps: string[];
      exclusions: string[];
      scan_window: string;
    };
    tools: string[];
  };
  legal_statement: string;
  requires_otp: boolean;
}

export interface VerifyAuthSignResponse {
  status: "signed";
  run_id: string;
  signed_at: string;
  signature_hash: string;
  expected_completion: string | null;
}
