import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { EvidenceVault } from "@/components/project/EvidenceVault";

export default async function EvidencePage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.evidence(params.id)} />
      <EvidenceVault projectId={params.id} />
    </div>
  );
}
