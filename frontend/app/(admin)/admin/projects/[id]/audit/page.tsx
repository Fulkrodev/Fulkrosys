import { A11AuditorVirtualButton } from "@/components/agents/A11AuditorVirtualButton";
import { AuditAccompanimentTimeline } from "@/components/audit/AuditAccompanimentTimeline";
import { AuditMode } from "@/components/audit/AuditMode";
import { MarkAuditPassedDialog } from "@/components/audit/MarkAuditPassedDialog";

export default function AuditPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-4">
      <AuditMode projectId={params.id} />
      <MarkAuditPassedDialog projectId={params.id} />
      <A11AuditorVirtualButton projectId={params.id} />
      <AuditAccompanimentTimeline projectId={params.id} />
    </div>
  );
}
