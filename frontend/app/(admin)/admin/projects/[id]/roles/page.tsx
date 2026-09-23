import { RoleTopologyPanelView } from "@/components/roles/RoleTopologyPanel";

export default async function RolesPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <RoleTopologyPanelView projectId={params.id} />;
}
