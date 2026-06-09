import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { ConformityCloudScoreCard } from "@/components/conformity/ConformityCloudScoreCard";
import { ConformityConsole } from "@/components/conformity/ConformityConsole";
import { ConformityWizard } from "@/components/conformity/ConformityWizard";

export default function ConformityPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.conformity(params.id)} />
      <ConformityWizard projectId={params.id} />
      <ConformityCloudScoreCard projectId={params.id} />
      <ConformityConsole projectId={params.id} />
    </div>
  );
}
