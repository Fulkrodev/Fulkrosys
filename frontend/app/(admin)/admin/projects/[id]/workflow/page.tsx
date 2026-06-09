/**
 * /admin/projects/[id]/workflow · Sub-area 2B Sesión 3B-2B.9 CLUSTER 2.
 *
 * Project-scoped thin wrapper R23 doctrine · reusa ProjectCronologicaView
 * (top-level WCC component · OPS-026 DRY) bajo ProjectLayout (sidebar/tabs
 * context). Misma vista cronológica admin R30 inverso:
 *   - 3 view modes (AHORA · Completa · Próximos pasos blockers)
 *   - 4 sections cronológicas (completed · ahora · proximos_7d · proximos_30d)
 *   - ProjectContextHeader + Kpi3MicroRow + 19 dims captured
 *   - WorkflowTimelineAdmin + WorkflowBlockersPanel
 *   - WorkflowStepDetailDrawerEnriched 5 tabs (detalle · actores · deliverables
 *     · adaptación · ens) cubre tasks per motor + evidence + cliente status
 *   - CopilotoAdminSidebar context-aware sticky right
 *
 * OPS-052 manifestación 65ª scope refined REFACTOR+EXTEND · empirical reveal
 * audit-first ProjectCronologicaView ya cubre 90% briefing target Sub-area 2B.
 *
 * Future-X capturados OPS-049 honest:
 *   - Future-1.E.workflow-audit-emit-admin-viewed (~1h) audit_log emit
 *     admin.workflow.viewed + admin.phase.transitioned via Sub-atom 5.A
 *     3-way OR pattern (project_id + client_id propagation)
 */
import { ProjectCronologicaView } from "@/components/workflow-command-center/ProjectCronologicaView";

export const metadata = {
  title: "Workflow del proyecto · FULKRO",
};

interface PageProps {
  params: { id: string };
  searchParams: { step?: string };
}

export default function ProjectWorkflowPage({ params, searchParams }: PageProps) {
  return (
    <ProjectCronologicaView
      projectId={params.id}
      initialStepId={searchParams.step}
    />
  );
}
