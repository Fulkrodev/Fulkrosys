import { WorkspacePanel } from "@/components/workspace/WorkspacePanel";

interface WorkspacePageProps {
  params: { id: string };
}

export default function WorkspacePage({ params }: WorkspacePageProps) {
  return <WorkspacePanel projectId={params.id} />;
}
