import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { RiskDashboard } from "@/components/project/RiskDashboard";

export default async function RisksPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.risks(params.id)} />
      <RiskDashboard projectId={params.id} />
    </div>
  );
}
