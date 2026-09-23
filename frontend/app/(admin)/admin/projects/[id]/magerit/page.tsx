import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { MageritPanel } from "@/components/project/MageritPanel";

export default async function MageritPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.magerit(params.id)} />
      <MageritPanel projectId={params.id} />
    </div>
  );
}
