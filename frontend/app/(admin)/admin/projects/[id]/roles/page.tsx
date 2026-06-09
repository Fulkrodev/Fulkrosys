import { RoleTopologyPanelView } from "@/components/roles/RoleTopologyPanel";

export default function RolesPage({
  params,
}: {
  params: { id: string };
}) {
  return <RoleTopologyPanelView projectId={params.id} />;
}
