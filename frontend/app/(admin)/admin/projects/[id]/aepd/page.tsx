import { AepdPanel } from "@/components/project/AepdPanel";

export default async function AepdPage(props: { params: Promise<{ id: string }> }) {
  const params = await props.params;
  return <AepdPanel projectId={params.id} />;
}
