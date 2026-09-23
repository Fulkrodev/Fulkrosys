import { ActionPlansPanel } from "@/components/project/ActionPlansPanel";

export default async function PlanesAccionPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ActionPlansPanel projectId={params.id} />;
}
