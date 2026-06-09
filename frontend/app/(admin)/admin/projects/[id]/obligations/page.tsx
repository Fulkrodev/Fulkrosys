import { ObligationBoard } from "@/components/project/ObligationBoard";

export default function ObligationsPage({
  params,
}: {
  params: { id: string };
}) {
  return <ObligationBoard projectId={params.id} />;
}
