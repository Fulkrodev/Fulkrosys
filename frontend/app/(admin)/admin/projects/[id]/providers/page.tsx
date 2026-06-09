import { ProvidersGrid } from "@/components/providers/ProvidersGrid";

export default function ProvidersPage({
  params,
}: {
  params: { id: string };
}) {
  return <ProvidersGrid projectId={params.id} />;
}
