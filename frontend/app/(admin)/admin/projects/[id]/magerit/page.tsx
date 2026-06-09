import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { MageritPanel } from "@/components/project/MageritPanel";

export default function MageritPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.magerit(params.id)} />
      <MageritPanel projectId={params.id} />
    </div>
  );
}
