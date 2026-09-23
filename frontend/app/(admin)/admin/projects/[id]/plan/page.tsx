import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { PdaGeneratorButton } from "@/components/project/PdaGeneratorButton";
import { PlanGantt } from "@/components/project/PlanGantt";

export default async function PlanPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="flex flex-col gap-4">
      <CopilotGuidedFlow {...PHASE_GUIDES.plan(params.id)} />
      <PlanGantt projectId={params.id} />
      <PdaGeneratorButton projectId={params.id} />
    </div>
  );
}
