/**
 * Client Tasks API · portal cliente workspace continuo
 * (ADR-038 SAN-D MB-14.3/4).
 *
 * Endpoints (cliente · usa clientApi wrapper · cookies + CSRF):
 *   GET  /api/v1/client-portal/tasks
 *   POST /api/v1/client-portal/tasks/{id}/start
 *   POST /api/v1/client-portal/tasks/{id}/complete
 *   POST /api/v1/client-portal/tasks/{id}/block (body: reason)
 */
import { clientApi } from "@/lib/client-portal-api";

export type ClientTaskStatus =
  | "pending"
  | "in_progress"
  | "blocked"
  | "done";

export interface ClientTask {
  id: string;
  project_id: string;
  template_id: string;
  phase: string;
  title: string;
  description: string | null;
  cta_label: string | null;
  cta_url: string | null;
  expected_evidence_type: string | null;
  expected_evidence_count: number;
  priority: number;
  status: ClientTaskStatus;
  due_date: string | null;
  started_at: string | null;
  completed_at: string | null;
  blocked_reason: string | null;
}

export const clientTasksApi = {
  list: (status?: ClientTaskStatus): Promise<ClientTask[]> => {
    const qs = status ? `?status_filter=${status}` : "";
    return clientApi<ClientTask[]>(`/client-portal/tasks${qs}`);
  },

  start: (taskId: string): Promise<ClientTask> =>
    clientApi<ClientTask>(`/client-portal/tasks/${taskId}/start`, {
      method: "POST",
    }),

  complete: (taskId: string): Promise<ClientTask> =>
    clientApi<ClientTask>(`/client-portal/tasks/${taskId}/complete`, {
      method: "POST",
    }),

  block: (taskId: string, reason: string): Promise<ClientTask> =>
    clientApi<ClientTask>(`/client-portal/tasks/${taskId}/block`, {
      method: "POST",
      json: { reason },
    }),

  // #27 Ola 6 · aprobación explícita y trazable del Plan de Adecuación
  // (audit_log plan.approved + done + SSE · NO es firma criptográfica).
  approvePlan: (taskId: string): Promise<ClientTask> =>
    clientApi<ClientTask>(`/client-portal/tasks/${taskId}/approve-plan`, {
      method: "POST",
    }),
};
