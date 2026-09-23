import { CommunicationPanel } from "@/components/project/CommunicationPanel";

export default async function CommunicationPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <CommunicationPanel projectId={params.id} />;
}
