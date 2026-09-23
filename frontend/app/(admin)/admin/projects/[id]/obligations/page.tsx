import { ObligationBoard } from "@/components/project/ObligationBoard";

export default async function ObligationsPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ObligationBoard projectId={params.id} />;
}
