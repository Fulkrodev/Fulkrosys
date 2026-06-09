/**
 * M8 Autopilot API client (doc §13-§14 · 2 gates humanos).
 *
 * Endpoints servidos (router montado con prefix `/api/v1`, require_owner · admin):
 *   POST /projects/{id}/verification/autopilot/start         → Gate 1 done → "Continuar"
 *   GET  /projects/{id}/verification/autopilot/status?run_id= → estado live del run
 *   GET  /projects/{id}/verification/metrics                 → observabilidad (§12)
 *   GET  /projects/{id}/verification/runs/{rid}/evidence-pack → evidencia ENAC (§16)
 *   POST /projects/{id}/verification/findings/{fid}/accept-risk → aceptación riesgo (§8)
 *   POST /projects/{id}/verification/runs/{rid}/attest        → Gate 2 atestación (Alto)
 *
 * SSE eventos admin canal `project:{id}` vía GET /api/v1/projects/{id}/events:
 *   m08_autopilot_started · m08_phase_change · m08_run_completed.
 *
 * Usa el wrapper `api` admin existente (BASE `/api/v1/...` · OPS-044) · R23 project-scoped.
 * Tipos espejo de los serializers Pydantic en m08_verification/autopilot_api.py +
 * observability/metrics.py + observability/evidence_pack.py.
 */
import { api } from "@/lib/api";

// ════════════════════════════════════════════════════════════════════
// Tipos de dominio
// ════════════════════════════════════════════════════════════════════

/** Categoría ENS aceptada por el backend (canónica o legacy BASICO/MEDIO/ALTO). */
export type AutopilotCategory = "BASICA" | "MEDIA" | "ALTA";

export type AutopilotStatus =
  | "authorized"
  | "running"
  | "paused_gate2"
  | "completed"
  | "partial"
  | "failed";

export type AutopilotPhase =
  | "recon"
  | "detection"
  | "normalization"
  | "verification"
  | "triage"
  | "reporting";

// ── start ──

export interface AutopilotStartBody {
  category: AutopilotCategory;
  mode?: "internal";
}

export interface AutopilotStartResponse {
  run_id: string;
  autopilot_status: AutopilotStatus;
  category: string;
  sse_channel: string;
  message: string;
}

// ── status ──

export interface AutopilotStatusResponse {
  run_id: string;
  category: string;
  mode: string;
  status: string;
  autopilot_status: AutopilotStatus;
  autopilot_phase: AutopilotPhase | null;
  coverage_pct: number | null;
  assets_in_scope: number | null;
  assets_scanned: number | null;
  partial_run: boolean;
  run_manifest_hash: string | null;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  tools_attempted: string[];
  tools_failed: string[];
  ephemeral_active: boolean;
  completed_at: string | null;
}

// ── metrics (§12) ──

export interface AutopilotMetricsCoverage {
  coverage_pct: number;
  assets_in_scope: number;
  assets_scanned: number;
  partial_run: boolean | null;
  run_id: string | null;
  autopilot_status: AutopilotStatus | null;
}

export interface AutopilotMetricsTrendPoint {
  run_id: string;
  completed_at: string | null;
  total: number;
  critical: number;
  high: number;
}

export interface AutopilotMetricsDrift {
  runs_with_manifest: number;
  distinct_manifests: number;
  drift_detected: boolean;
}

export interface AutopilotMetricsPipelineHealth {
  total_runs: number;
  partial_runs: number;
  failed_runs: number;
  partial_rate: number;
  failed_rate: number;
}

export interface AutopilotMetricsResponse {
  coverage: AutopilotMetricsCoverage;
  fp_rate_post_gate4: number;
  fp_post_gate4_total: number;
  mttr_hours_by_severity: Record<string, number | null>;
  finding_trend: AutopilotMetricsTrendPoint[];
  determinism_drift: AutopilotMetricsDrift;
  pipeline_health: AutopilotMetricsPipelineHealth;
}

// ── evidence pack (§16) ──

export interface EvidencePackFindingByMeasure {
  finding_id: string;
  title: string;
  severity: string;
  state: string;
  verification_level: string;
  zero_fp_verified: boolean;
}

export interface EvidencePackEvidenceEntry {
  ts: string | null;
  actor: string | null;
  action: string | null;
  component: string | null;
  ens_relevance: string | null;
}

export interface EvidencePackResponse {
  run_id: string;
  project_id: string;
  categoria_ens: string | null;
  metodologia: string[];
  autorizacion: {
    authorized_by: string | null;
    authorization_signed_at: string | null;
    ephemeral_session: string | null;
    ephemeral_revoked_at: string | null;
  };
  determinismo: {
    run_manifest_hash: string | null;
    golden_run_id: string | null;
  };
  cobertura: {
    coverage_pct: number;
    assets_in_scope: number | null;
    assets_scanned: number | null;
    partial_run: boolean;
    tools_attempted: string[];
    tools_failed: string[];
  };
  hallazgos: {
    total: number;
    zero_fp_verified: number;
    por_medida_ens: Record<string, EvidencePackFindingByMeasure[]>;
    por_estado: Record<string, number>;
    severidad: {
      critical: number;
      high: number;
      medium: number;
      low: number;
      info: number;
    };
  };
  cierre: {
    closed: number;
    risk_accepted: number;
    delta_new: number;
    delta_resolved: number;
    delta_persistent: number;
  };
  evidence_trail: EvidencePackEvidenceEntry[];
  integridad_r6: {
    ok: boolean | null;
    total?: number;
    first_bad_seq?: number | null;
    note?: string;
  };
  gate2_atestacion: {
    required: boolean;
    status: AutopilotStatus | string | null;
    done: boolean;
    external_pentester?: string | null;
    cert?: string | null;
  };
  disclaimer: string;
}

// ── accept-risk (§8) ──

export interface AcceptRiskBody {
  justification: string;
  approved_by: string;
  /** ISO-8601 datetime · caducidad de la aceptación de riesgo. */
  expires_at: string;
}

export interface AcceptRiskResponse {
  finding_id: string;
  finding_state: string;
  risk_acceptance: Record<string, unknown>;
}

// ── attest / Gate 2 (§14) ──

export interface AttestBody {
  attested_by: string;
  cert?: string;
  opinion?: string;
}

export interface AttestResponse {
  run_id: string;
  autopilot_status: AutopilotStatus;
  attested_by: string;
}

// ════════════════════════════════════════════════════════════════════
// Labels / variantes (presentación)
// ════════════════════════════════════════════════════════════════════

export const AUTOPILOT_STATUS_LABELS: Record<AutopilotStatus, string> = {
  authorized: "Autorizado",
  running: "Ejecutando",
  paused_gate2: "Pausado · Gate 2",
  completed: "Completado",
  partial: "Parcial",
  failed: "Fallido",
};

export const AUTOPILOT_STATUS_VARIANTS: Record<
  AutopilotStatus,
  "secondary" | "info" | "warning" | "success" | "danger"
> = {
  authorized: "secondary",
  running: "info",
  paused_gate2: "warning",
  completed: "success",
  partial: "warning",
  failed: "danger",
};

/** Orden canónico de fases del pipeline (doc §13). */
export const AUTOPILOT_PHASES: AutopilotPhase[] = [
  "recon",
  "detection",
  "normalization",
  "verification",
  "triage",
  "reporting",
];

export const AUTOPILOT_PHASE_LABELS: Record<AutopilotPhase, string> = {
  recon: "Reconocimiento",
  detection: "Detección",
  normalization: "Normalización",
  verification: "Verificación",
  triage: "Triaje",
  reporting: "Informe",
};

/** SSE event types admin (canal project:{id}). */
export const AUTOPILOT_SSE_EVENTS = [
  "m08_autopilot_started",
  "m08_phase_change",
  "m08_run_completed",
] as const;
export type AutopilotSseEvent = (typeof AUTOPILOT_SSE_EVENTS)[number];

// ════════════════════════════════════════════════════════════════════
// API surface
// ════════════════════════════════════════════════════════════════════

export const autopilotApi = {
  /** Gate 1 superado → "Continuar": crea el run y lanza el autopilot. */
  start: (projectId: string, body: AutopilotStartBody) =>
    api<AutopilotStartResponse>(
      `/api/v1/projects/${projectId}/verification/autopilot/start`,
      { json: { mode: "internal", ...body } },
    ),

  /** Estado live (run concreto o el último del proyecto). */
  getStatus: (projectId: string, runId?: string | null) =>
    api<AutopilotStatusResponse>(
      `/api/v1/projects/${projectId}/verification/autopilot/status${
        runId ? `?run_id=${encodeURIComponent(runId)}` : ""
      }`,
    ),

  /** Observabilidad (§12). */
  getMetrics: (projectId: string) =>
    api<AutopilotMetricsResponse>(
      `/api/v1/projects/${projectId}/verification/metrics`,
    ),

  /** Pack de evidencia ENAC (§16) para un run. */
  getEvidencePack: (projectId: string, runId: string) =>
    api<EvidencePackResponse>(
      `/api/v1/projects/${projectId}/verification/runs/${runId}/evidence-pack`,
    ),

  /** Aceptación de riesgo con justificación + autoridad + caducidad (§8). */
  acceptRisk: (projectId: string, findingId: string, body: AcceptRiskBody) =>
    api<AcceptRiskResponse>(
      `/api/v1/projects/${projectId}/verification/findings/${findingId}/accept-risk`,
      { json: body },
    ),

  /** Gate 2 atestación (Alto · §14) · cierra el run pausado en paused_gate2. */
  attest: (projectId: string, runId: string, body: AttestBody) =>
    api<AttestResponse>(
      `/api/v1/projects/${projectId}/verification/runs/${runId}/attest`,
      { json: body },
    ),

  /**
   * SSE stream URL admin (canal project:{id}).
   * Consume via `new EventSource(url, { withCredentials: true })`.
   */
  streamUrl: (projectId: string): string =>
    `/api/v1/projects/${projectId}/events`,
};

// ── helpers de funciones nombradas (paridad con pentest.ts) ──

export const startAutopilot = autopilotApi.start;
export const getAutopilotStatus = autopilotApi.getStatus;
export const getAutopilotMetrics = autopilotApi.getMetrics;
export const getEvidencePack = autopilotApi.getEvidencePack;
export const acceptRisk = autopilotApi.acceptRisk;
export const attestRun = autopilotApi.attest;
