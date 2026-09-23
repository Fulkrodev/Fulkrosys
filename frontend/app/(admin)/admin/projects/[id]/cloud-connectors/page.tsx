import { CloudConnectorsAdminPanel } from "@/components/cloud-connectors/CloudConnectorsAdminPanel";

export default async function ProjectCloudConnectorsPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <CloudConnectorsAdminPanel projectId={params.id} />;
}
