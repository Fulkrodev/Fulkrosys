import { DiscrepanciesPanel } from "@/components/agents/DiscrepanciesPanel";

export default async function DiscrepanciesPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <DiscrepanciesPanel projectId={params.id} />;
}
