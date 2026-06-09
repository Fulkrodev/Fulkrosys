/**
 * API cliente · M17 Plan READ-ONLY (Sesión 3B-2B.8 Phase 1E).
 *
 * Endpoint backend: GET /api/v1/client-portal/plan
 * Schema: ClienteTimelineResponse mirror admin TimelineResponse + `responsible`
 * field expuesto cliente filter "Mis tareas".
 *
 * R29 sostained · friendly response · ADR-014 read-only (NO POST/PATCH/DELETE).
 */
import { clientApi } from "@/lib/client-portal-api";

export type Responsible = "marcos" | "cliente" | "plataforma" | "mixto";

export interface ClienteTimelineTask {
  id: string;
  task_code: string;
  task_name: string;
  phase: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string | null;
  progress_pct: number;
  is_critical_path: boolean;
  responsible: Responsible | string | null;
}

export interface ClienteTimelineMilestone {
  name: string;
  date: string | null;
  type: string;
  status: string | null;
}

export interface ClienteTimelineResponse {
  plan_start: string | null;
  plan_end: string | null;
  tasks: ClienteTimelineTask[];
  milestones: ClienteTimelineMilestone[];
  plan_estado: string | null;
  project_id: string;
}

export async function fetchClientePlan(): Promise<ClienteTimelineResponse> {
  return clientApi<ClienteTimelineResponse>("/client-portal/plan");
}

/** Cliente-side filter helper · "Solo mis tareas" toggle. */
export function isClienteTask(task: ClienteTimelineTask): boolean {
  return task.responsible === "cliente" || task.responsible === "mixto";
}
