import { DiscrepanciesPanel } from "@/components/agents/DiscrepanciesPanel";

export default function DiscrepanciesPage({
  params,
}: {
  params: { id: string };
}) {
  return <DiscrepanciesPanel projectId={params.id} />;
}
