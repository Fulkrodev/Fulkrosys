import { AuditDryRunDashboard } from "@/components/audit-dry-run/AuditDryRunDashboard";

export default async function AuditDryRunPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Audit Dry-Run · A11 + M10</h1>
      <AuditDryRunDashboard projectId={params.id} />
    </div>
  );
}
