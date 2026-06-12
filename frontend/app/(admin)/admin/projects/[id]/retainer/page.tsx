import { RetainerCheckinAdminPanel } from "@/components/retainer/RetainerCheckinAdminPanel";
import { RetainerProjectDashboard } from "@/components/retainer/RetainerDashboard";

export default function RetainerProjectPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <RetainerProjectDashboard projectId={params.id} />
      <RetainerCheckinAdminPanel projectId={params.id} />
    </div>
  );
}
