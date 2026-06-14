import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { McpProjectScopedPanel } from "@/components/mcps/McpProjectScopedPanel";

export default function ProjectMcpsPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="flex flex-col gap-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.mcps(params.id)} />
      <McpProjectScopedPanel projectId={params.id} />
    </div>
  );
}
