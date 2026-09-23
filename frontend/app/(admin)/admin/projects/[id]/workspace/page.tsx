import { WorkspacePanel } from "@/components/workspace/WorkspacePanel";

interface WorkspacePageProps {
  params: Promise<{ id: string }>;
}

export default async function WorkspacePage(props: WorkspacePageProps) {
  const params = await props.params;
  return <WorkspacePanel projectId={params.id} />;
}
