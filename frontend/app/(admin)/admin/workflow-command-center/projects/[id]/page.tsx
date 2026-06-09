/**
 * /admin/workflow-command-center/projects/[id] · vista maestra per-cliente.
 *
 * Sub-atom 1.C.D.B.2 v3.8 · ProjectContextHeader + WorkflowTimelineAdmin
 * (4 sections cronológicas) + Drawer 5 tabs UX premium.
 *
 * Layout 3-col integration deferred 1.C.D.B.3 (CopilotoAdminSidebar stub).
 * Por ahora layout 2-col conservador · centro 75% + container max-width.
 */
import { ProjectCronologicaView } from "@/components/workflow-command-center/ProjectCronologicaView";

export const metadata = {
  title: "Vista cronológica del proyecto · FULKRO",
};

interface PageProps {
  params: { id: string };
  searchParams: { step?: string };
}

export default function ProjectCronologicaPage({ params, searchParams }: PageProps) {
  return (
    <div className="mx-auto max-w-7xl">
      <ProjectCronologicaView
        projectId={params.id}
        initialStepId={searchParams.step}
      />
    </div>
  );
}
