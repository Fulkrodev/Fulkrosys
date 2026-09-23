import { DiscoveryPanel } from "@/components/discovery/DiscoveryPanel";

interface DiscoveryPageProps {
  params: Promise<{ id: string }>;
}

export default async function DiscoveryPage(props: DiscoveryPageProps) {
  const params = await props.params;
  return <DiscoveryPanel projectId={params.id} />;
}
