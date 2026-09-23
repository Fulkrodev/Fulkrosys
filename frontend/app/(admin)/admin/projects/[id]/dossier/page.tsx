import { CopilotGuidedFlow } from "@/components/admin/copilot/CopilotGuidedFlow";
import { PHASE_GUIDES } from "@/components/admin/copilot/phaseGuides";
import { DossierPreview } from "@/components/project/DossierPreview";

export default async function DossierPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <CopilotGuidedFlow {...PHASE_GUIDES.dossier(params.id)} />
      <DossierPreview projectId={params.id} />
    </div>
  );
}
