import { BiaPanel } from "@/components/project/BiaPanel";

export default function BiaPage({ params }: { params: { id: string } }) {
  return <BiaPanel projectId={params.id} />;
}
