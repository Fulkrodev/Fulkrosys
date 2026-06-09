/**
 * API client · Action Plans Dashboard K.3 cross-motor.
 *
 * Endpoint prefix `/api/v1` admin-only require_owner.
 * Aggregator combines M04 gap + M09 audit_prep + A21 discrepancies findings.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1";

export type ActionPlanSeverity = "critica" | "alta" | "media" | "baja";
export type ActionPlanSource =
  | "m04_gap"
  | "m09_audit_prep"
  | "m19_incident"
  | "a21_discrepancy";
export type ActionPlanFamilia = "org" | "op" | "mp" | "cross";
export type ActionPlanEstado =
  | "abierto"
  | "en_curso"
  | "cerrado"
  | "descartado";

export interface ActionPlanItem {
  id: string;
  source: ActionPlanSource;
  severity: ActionPlanSeverity;
  familia: ActionPlanFamilia;
  medida_afectada: string | null;
  description: string;
  responsable: string | null;
  estado: ActionPlanEstado;
  fecha_objetivo: string | null;
  project_id: string;
  motor_link: string | null;
}

export interface ActionPlansResponse {
  project_id: string;
  total_count: number;
  counts_by_source: Record<string, number>;
  counts_by_severity: Record<string, number>;
  items: ActionPlanItem[];
}

export interface ActionPlansListOptions {
  limit?: number;
  severity?: ActionPlanSeverity[];
  estado?: ActionPlanEstado[];
  source?: ActionPlanSource[];
}

export const actionPlansApi = {
  list: (
    projectId: string,
    opts: ActionPlansListOptions = {},
  ) => {
    const sp = new URLSearchParams();
    if (opts.limit) sp.set("limit", String(opts.limit));
    for (const s of opts.severity ?? []) sp.append("severity", s);
    for (const e of opts.estado ?? []) sp.append("estado", e);
    for (const s of opts.source ?? []) sp.append("source", s);
    const qs = sp.toString();
    return api<ActionPlansResponse>(
      `${BASE}/projects/${projectId}/action-plans${qs ? `?${qs}` : ""}`,
    );
  },
};
