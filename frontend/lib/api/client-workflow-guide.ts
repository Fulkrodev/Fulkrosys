/**
 * Client Workflow Guide API · sub-atom 1.C.D.C.1 v3.8.
 *
 * Consume endpoint subset friendly cliente:
 *   GET /api/v1/projects/{id}/workflow-guide → WorkflowGuideResponse
 *
 * Reusa types EnrichedStepState desde lib/api/workflow-command-center
 * (same backend model · workflow_engine emite mismo shape · solo expone subset).
 *
 * OPS-044 sostenido · usa clientApi wrapper (cliente cookie auth + CSRF) ·
 * path SIN double prefix (clientApi ya prepend /api/v1).
 */
import { clientApi } from "@/lib/client-portal-api";
import type {
  EnrichedStepState,
  ProgressResponse,
} from "@/lib/api/workflow-command-center";

export type { EnrichedStepState };

export interface WorkflowGuideResponse {
  project_id: string;
  categoria: string | null;
  archetype: string | null;
  fase: string;
  progress: ProgressResponse;
  current_step: EnrichedStepState | null;
  completed: EnrichedStepState[];
  proximos: EnrichedStepState[];
}

export const clientWorkflowGuideApi = {
  /**
   * Workflow guide friendly cliente · subset enriched.
   * NO 30d forecast · NO admin actions · vista calm cronológica.
   */
  get: (projectId: string): Promise<WorkflowGuideResponse> =>
    clientApi<WorkflowGuideResponse>(`/projects/${projectId}/workflow-guide`),

  /**
   * Progress breakdown reusable (% global + per phase).
   */
  progress: (projectId: string): Promise<ProgressResponse> =>
    clientApi<ProgressResponse>(`/projects/${projectId}/workflow-engine/progress`),
};
