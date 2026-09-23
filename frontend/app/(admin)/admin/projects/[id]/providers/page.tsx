import { ProvidersGrid } from "@/components/providers/ProvidersGrid";

export default async function ProvidersPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ProvidersGrid projectId={params.id} />;
}
