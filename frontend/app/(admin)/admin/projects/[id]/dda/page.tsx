import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { DdaAdminPanel } from "@/components/m03_dda/DdaAdminPanel";

export default function DdaAdminPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.dda(params.id)} />
      <DdaAdminPanel projectId={params.id} />
    </div>
  );
}
