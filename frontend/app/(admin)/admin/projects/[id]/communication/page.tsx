import { CommunicationPanel } from "@/components/project/CommunicationPanel";

export default function CommunicationPage({
  params,
}: {
  params: { id: string };
}) {
  return <CommunicationPanel projectId={params.id} />;
}
