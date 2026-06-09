import { AuditDryRunDashboard } from "@/components/audit-dry-run/AuditDryRunDashboard";

export default function AuditDryRunPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Audit Dry-Run · A11 + M10</h1>
      <AuditDryRunDashboard projectId={params.id} />
    </div>
  );
}
