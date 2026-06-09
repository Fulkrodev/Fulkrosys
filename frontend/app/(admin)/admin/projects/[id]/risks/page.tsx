import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { RiskDashboard } from "@/components/project/RiskDashboard";

export default function RisksPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.risks(params.id)} />
      <RiskDashboard projectId={params.id} />
    </div>
  );
}
