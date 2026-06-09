import { ActionPlansPanel } from "@/components/project/ActionPlansPanel";

export default function PlanesAccionPage({
  params,
}: {
  params: { id: string };
}) {
  return <ActionPlansPanel projectId={params.id} />;
}
