/**
 * Workflow blocking API client (ADR-036 SAN-D MB-17.5).
 *
 * GET /api/v1/projects/{id}/workflow/can-transition/{phase}.
 * POST /transition deferrable a MB-18 (DEC-5 ADR-036).
 */
import { api } from "@/lib/api";

export interface BlockingIssue {
  feature_key: string;
  description: string;
  target_phase: number;
  fix_url: string;
}

export interface WorkflowBlockingResult {
  can_transition: boolean;
  target_phase: number;
  target_phase_label: string;
  blocking_issues: BlockingIssue[];
}

export const workflowApi = {
  canTransition: (
    projectId: string,
    targetPhase: number,
  ): Promise<WorkflowBlockingResult> =>
    api<WorkflowBlockingResult>(
      `/api/v1/projects/${projectId}/workflow/can-transition/${targetPhase}`,
    ),
};
