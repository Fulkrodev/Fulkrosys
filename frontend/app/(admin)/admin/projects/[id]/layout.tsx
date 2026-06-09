import { QuickActions } from "@/components/dashboard/QuickActions";
import { ActiveProjectSync } from "@/components/layout/ActiveProjectSync";
import { ProjectBreadcrumb } from "@/components/layout/ProjectBreadcrumb";
import { ProjectCategoryBanner } from "@/components/project/ProjectCategoryBanner";
import { ProjectHeader } from "@/components/project/ProjectHeader";
import { ProjectTabs } from "@/components/project/ProjectTabs";
import { ProjectFeaturesProvider } from "@/lib/contexts/ProjectFeaturesContext";

export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { id: string };
}) {
  return (
    <ProjectFeaturesProvider projectId={params.id}>
      {/* Sub-atom 1.E.2 Phase C · ADR-054 · routing guard sync activeProject
          store con URL param. Headless (returns null). */}
      <ActiveProjectSync projectId={params.id} />
      <div className="flex flex-col gap-7">
        {/* Breadcrumb persistent project-scoped pages */}
        <ProjectBreadcrumb />
        <ProjectHeader projectId={params.id} />
        <ProjectCategoryBanner />
        <QuickActions />
        <ProjectTabs projectId={params.id} />
        <div>{children}</div>
      </div>
    </ProjectFeaturesProvider>
  );
}
