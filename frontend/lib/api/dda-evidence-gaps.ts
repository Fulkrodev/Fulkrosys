/**
 * DdA-Evidence gap API client · CLUSTER 3 Phase C3.3.
 *
 * Wraps backend `/api/v1/public/auditor-portal/{token}/audit/dda-evidence-gaps/*`
 * (auditor) + `/api/v1/admin/projects/{project_id}/audit/dda-evidence-gaps/*`
 * (admin) + `/audit/request-more-evidence` (admin POST).
 */
import { api } from "@/lib/api";

const PUBLIC_BASE = "/api/v1/public/auditor-portal";
const ADMIN_BASE = "/api/v1/admin/projects";

export type GapStatus =
  | "covered"
  | "partial"
  | "missing"
  | "not_applicable";

export type GapSeverity = "critical" | "high" | "medium" | "low";

export interface EvidenceSummaryItem {
  id: string;
  nombre_tipo: string | null;
  fichero_nombre_original: string | null;
  fecha_evidencia: string | null;
  vigente: boolean;
}

export interface MedidaGapRow {
  medida_code: string;
  medida_nombre: string | null;
  family: string | null;
  categoria_minima: string | null;
  aplicabilidad_dda: string | null;
  status: GapStatus;
  severity: GapSeverity;
  evidence_count: number;
  min_required: number;
  last_uploaded_at: string | null;
  stale: boolean;
  gap_reason: string | null;
  evidences_summary: EvidenceSummaryItem[];
}

export interface GapSeveritySummary {
  critical_missing: number;
  high_partial: number;
  medium_total: number;
  low_total: number;
  recoverable: number;
}

export interface DdaEvidenceGapMatrix {
  project_id: string;
  categoria: string | null;
  total_applicable: number;
  total_covered: number;
  total_partial: number;
  total_missing: number;
  total_not_applicable: number;
  coverage_pct: number;
  medidas: MedidaGapRow[];
  severity_summary: GapSeveritySummary;
  options_used: {
    min_required_per_measure: number;
    stale_threshold_days: number;
    critical_high_requirement: number;
    skip_no_aplica: boolean;
    require_vigente: boolean;
  };
  computed_at: string;
}

// ══════════════════════════════════════════════════════════════════════
// Auditor portal API
// ══════════════════════════════════════════════════════════════════════

export async function getDdaEvidenceGapsAuditor(
  token: string,
): Promise<DdaEvidenceGapMatrix> {
  return api<DdaEvidenceGapMatrix>(
    `${PUBLIC_BASE}/${token}/audit/dda-evidence-gaps`,
  );
}

export async function getMedidaDetailAuditor(
  token: string,
  medidaCode: string,
): Promise<MedidaGapRow> {
  return api<MedidaGapRow>(
    `${PUBLIC_BASE}/${token}/audit/dda-evidence-gaps/medida/${encodeURIComponent(
      medidaCode,
    )}`,
  );
}

// ══════════════════════════════════════════════════════════════════════
// Admin API
// ══════════════════════════════════════════════════════════════════════

export async function getDdaEvidenceGapsAdmin(
  projectId: string,
): Promise<DdaEvidenceGapMatrix> {
  return api<DdaEvidenceGapMatrix>(
    `${ADMIN_BASE}/${projectId}/audit/dda-evidence-gaps`,
  );
}

export interface RequestMoreEvidenceBody {
  medida_codes: string[];
  message_to_client?: string;
}

export interface RequestMoreEvidenceResponse {
  notification_id: string | null;
  medida_codes: string[];
  triggered_at: string;
}

export async function requestMoreEvidenceAdmin(
  projectId: string,
  body: RequestMoreEvidenceBody,
): Promise<RequestMoreEvidenceResponse> {
  return api<RequestMoreEvidenceResponse>(
    `${ADMIN_BASE}/${projectId}/audit/request-more-evidence`,
    { json: body },
  );
}

// ══════════════════════════════════════════════════════════════════════
// UI helpers
// ══════════════════════════════════════════════════════════════════════

export const STATUS_LABEL: Record<GapStatus, string> = {
  covered: "Cubierta",
  partial: "Parcial",
  missing: "Sin evidencia",
  not_applicable: "No aplica",
};

export const STATUS_COLOR_CLASS: Record<GapStatus, string> = {
  covered: "bg-fulkro-success-700/20 border-fulkro-success-700/40 text-fulkro-success-700",
  partial: "bg-fulkro-warning-700/20 border-fulkro-warning-700/40 text-fulkro-warning-700",
  missing: "bg-fulkro-danger-700/20 border-fulkro-danger-700/40 text-fulkro-danger-700",
  not_applicable: "bg-fulkro-ink-300/20 border-fulkro-ink-300 text-fulkro-ink-500",
};

export const SEVERITY_LABEL: Record<GapSeverity, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Medio",
  low: "Bajo",
};

export const SEVERITY_VARIANT: Record<
  GapSeverity,
  "danger" | "warning" | "info" | "outline"
> = {
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "outline",
};

export const FAMILY_LABEL: Record<string, string> = {
  org: "Marco organizativo",
  op: "Marco operacional",
  mp: "Medidas de protección",
};
