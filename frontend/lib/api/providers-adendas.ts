/**
 * API client · Motor 14 Providers · sub-contracts/adendas FASE C Phase C.
 *
 * Endpoints servidos desde m14 con prefix `/api/v1/projects/{id}/providers`:
 *   GET  /api/v1/projects/{id}/providers/adendas
 *   POST /api/v1/projects/{id}/providers/adenda/check
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/projects";

export type AdendaTrigger =
  | "workflow_step_completed"
  | "materiality_material_cascade"
  | "admin_manual"
  | "manual";

export const ADENDA_TRIGGER_LABELS: Record<AdendaTrigger, string> = {
  workflow_step_completed: "Hito workflow",
  materiality_material_cascade: "Cambio material M28",
  admin_manual: "Admin manual",
  manual: "Manual (legacy)",
};

export const ADENDA_TRIGGER_VARIANTS: Record<
  AdendaTrigger,
  "secondary" | "warning" | "success" | "outline"
> = {
  workflow_step_completed: "success",
  materiality_material_cascade: "warning",
  admin_manual: "secondary",
  manual: "outline",
};

export interface AdendaTriggerHistoryEntry {
  trigger: AdendaTrigger;
  auto_generated_at: string;
  completed_template_id?: string;
  materiality_change_id?: string;
  materiality_level?: string;
  materiality_flags_triggered?: string[];
  admin_user_id?: string;
}

export interface AdendaSummary {
  addendum_id: string;
  addendum_code: string;
  provider_id: string;
  contract_ref: string | null;
  normativas_cubiertas: string[];
  template_code: string | null;
  firmado_cliente: boolean;
  firmado_proveedor: boolean;
  fecha_firma: string | null;
  fecha_vigor: string | null;
  vencimiento: string | null;
  created_at: string | null;
  audit_trail: {
    last_trigger: AdendaTrigger;
    last_auto_generated_at: string | null;
    triggers_history: AdendaTriggerHistoryEntry[];
  };
}

export interface AdendasListResponse {
  project_id: string;
  count: number;
  adendas: AdendaSummary[];
}

export interface AdendaCheckResponse {
  project_id: string;
  trigger_template_id: string;
  adendas_processed: number;
  details: Array<{
    provider_id: string;
    addendum_code: string;
    addendum_id: string;
    trigger: AdendaTrigger | string;
    completed_template_id?: string;
    materiality_change_id?: string;
    materiality_flags?: string[];
  }>;
}

export const providersAdendasApi = {
  list: (projectId: string) =>
    api<AdendasListResponse>(`${BASE}/${projectId}/providers/adendas`),

  triggerCheck: (
    projectId: string,
    body: { completed_template_id?: string } = {},
  ) =>
    api<AdendaCheckResponse>(`${BASE}/${projectId}/providers/adenda/check`, {
      json: body,
    }),
};
