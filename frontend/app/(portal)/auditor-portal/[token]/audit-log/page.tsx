import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { AuditLogView } from "@/components/auditor-portal/views/AuditLogView";

export const metadata = { title: "Portal auditor · Audit log" };

export default function AuditorPortalAuditLogPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <AuditLogView token={params.token} />
    </AuditorPortalEntry>
  );
}
