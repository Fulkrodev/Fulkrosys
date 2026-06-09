import { AepdPanel } from "@/components/project/AepdPanel";

export default function AepdPage({ params }: { params: { id: string } }) {
  return <AepdPanel projectId={params.id} />;
}
