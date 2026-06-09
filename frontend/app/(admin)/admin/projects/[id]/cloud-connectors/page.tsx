import { CloudConnectorsAdminPanel } from "@/components/cloud-connectors/CloudConnectorsAdminPanel";

export default function ProjectCloudConnectorsPage({
  params,
}: {
  params: { id: string };
}) {
  return <CloudConnectorsAdminPanel projectId={params.id} />;
}
