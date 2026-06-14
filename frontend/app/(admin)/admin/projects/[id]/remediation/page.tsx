import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { RemediationConsolePanel } from "@/components/remediation/RemediationConsolePanel";

export default function ProjectRemediationPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="flex flex-col gap-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.remediation(params.id)} />
      <RemediationConsolePanel projectId={params.id} />
    </div>
  );
}
