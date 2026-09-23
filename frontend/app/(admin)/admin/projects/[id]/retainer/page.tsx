import { RetainerCheckinAdminPanel } from "@/components/retainer/RetainerCheckinAdminPanel";
import { RetainerProjectDashboard } from "@/components/retainer/RetainerDashboard";

export default async function RetainerProjectPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <RetainerProjectDashboard projectId={params.id} />
      <RetainerCheckinAdminPanel projectId={params.id} />
    </div>
  );
}
