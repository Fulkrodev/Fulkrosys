import { AwarenessPanel } from "@/components/project/AwarenessPanel";

export default function AwarenessPage({
  params,
}: {
  params: { id: string };
}) {
  return <AwarenessPanel projectId={params.id} />;
}
