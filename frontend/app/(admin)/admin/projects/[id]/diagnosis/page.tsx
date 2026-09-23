import { IsoCoveragePanel } from "@/components/diagnosis/IsoCoveragePanel";
import { DiagnosisPanel } from "@/components/project/DiagnosisPanel";

export default async function DiagnosisPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="flex flex-col gap-4">
      <DiagnosisPanel projectId={params.id} />
      <IsoCoveragePanel projectId={params.id} />
    </div>
  );
}
