/**
 * Adaptive dashboard API · MB-7 atom 7.1 plan v6.
 *
 * Q5.2 + Q5.3 cement: NO role dimension. 4-dim context = tier + phase +
 * archetype + sector. Returned by GET /api/v1/client-portal/dashboard/adaptive.
 */
import { clientApi } from "@/lib/client-portal-api";

export type WorkflowPhase =
  | "onboarding"
  | "diagnostico"
  | "magerit"
  | "dda"
  | "implantacion"
  | "verificacion"
  | "auditoria"
  | "conformidad"
  | "retainer_cierre"
  | "retainer_activo";

export interface DashboardContext {
  client_id: string;
  client_name: string | null;
  project_id: string;
  project_name: string | null;
  categoria_objetivo: "BASICA" | "MEDIA" | "ALTA" | null;
  current_phase: WorkflowPhase | string | null;
  archetype: string | null;
  sector: string | null;
  days_to_certification: number | null;
  phase_step: number | null;
  phase_total: number;
}

export interface AdaptiveAction {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: string;
  estimated_minutes: number;
  priority: "high" | "medium" | "low";
  requires_step_up: boolean;
}

export interface WorkflowSummary {
  phase: string | null;
  phase_step: number | null;
  phase_total: number;
  dda_pending: number;
  evidence_pending: number;
  risks_open: number;
  magerit_assets_pending: number;
  archetype_hint: string;
}

export interface RecentMessage {
  id: string;
  sender_type: string;
  preview: string;
  created_at: string | null;
}

export interface AdaptiveDashboardResponse {
  context: DashboardContext;
  today_actions: AdaptiveAction[];
  workflow_summary: WorkflowSummary;
  recent_messages: RecentMessage[];
  new_documents_count: number;
  upcoming_invoice: Record<string, unknown> | null;
  notifications_unread: number;
  whatsapp_thread_id: string | null;
}

export async function fetchAdaptiveDashboard(): Promise<AdaptiveDashboardResponse> {
  return clientApi<AdaptiveDashboardResponse>("/client-portal/dashboard/adaptive");
}
