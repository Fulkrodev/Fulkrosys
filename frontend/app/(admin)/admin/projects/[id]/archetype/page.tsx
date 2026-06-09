import { ArchetypePanel } from "@/components/project/ArchetypePanel";

export default function ArchetypePage({
  params,
}: {
  params: { id: string };
}) {
  return <ArchetypePanel projectId={params.id} />;
}
