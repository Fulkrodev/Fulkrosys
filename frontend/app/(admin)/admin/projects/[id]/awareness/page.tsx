import { AwarenessPanel } from "@/components/project/AwarenessPanel";

export default async function AwarenessPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <AwarenessPanel projectId={params.id} />;
}
