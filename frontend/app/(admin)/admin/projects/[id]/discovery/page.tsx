import { DiscoveryPanel } from "@/components/discovery/DiscoveryPanel";

interface DiscoveryPageProps {
  params: { id: string };
}

export default function DiscoveryPage({ params }: DiscoveryPageProps) {
  return <DiscoveryPanel projectId={params.id} />;
}
