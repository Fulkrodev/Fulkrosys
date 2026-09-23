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
  params: Promise<{ id: string }>;
  searchParams: Promise<{ step?: string }>;
}

export default async function ProjectCronologicaPage(props: PageProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;
  return (
    <div className="mx-auto max-w-7xl">
      <ProjectCronologicaView
        projectId={params.id}
        initialStepId={searchParams.step}
      />
    </div>
  );
}
