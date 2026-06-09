import { ObligationBoard } from "@/components/project/ObligationBoard";

export default function ImplementationPage({
  params,
}: {
  params: { id: string };
}) {
  return <ObligationBoard projectId={params.id} />;
}
