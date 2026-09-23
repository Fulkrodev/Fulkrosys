import { ArchetypePanel } from "@/components/project/ArchetypePanel";

export default async function ArchetypePage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ArchetypePanel projectId={params.id} />;
}
