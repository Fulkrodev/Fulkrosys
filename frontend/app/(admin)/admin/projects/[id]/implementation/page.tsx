import { ObligationBoard } from "@/components/project/ObligationBoard";

export default async function ImplementationPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ObligationBoard projectId={params.id} />;
}
