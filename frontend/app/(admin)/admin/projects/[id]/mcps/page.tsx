import { McpProjectScopedPanel } from "@/components/mcps/McpProjectScopedPanel";

export default function ProjectMcpsPage({
  params,
}: {
  params: { id: string };
}) {
  return <McpProjectScopedPanel projectId={params.id} />;
}
