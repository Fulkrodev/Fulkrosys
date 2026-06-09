import { IsoCoveragePanel } from "@/components/diagnosis/IsoCoveragePanel";
import { DiagnosisPanel } from "@/components/project/DiagnosisPanel";

export default function DiagnosisPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="flex flex-col gap-4">
      <DiagnosisPanel projectId={params.id} />
      <IsoCoveragePanel projectId={params.id} />
    </div>
  );
}
