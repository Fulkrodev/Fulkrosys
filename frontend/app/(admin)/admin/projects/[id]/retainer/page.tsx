import { RetainerProjectDashboard } from "@/components/retainer/RetainerDashboard";

export default function RetainerProjectPage({
  params,
}: {
  params: { id: string };
}) {
  return <RetainerProjectDashboard projectId={params.id} />;
}
