import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { AuditLogView } from "@/components/auditor-portal/views/AuditLogView";

export const metadata = { title: "Portal auditor · Audit log" };

export default async function AuditorPortalAuditLogPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <AuditLogView token={params.token} />
    </AuditorPortalEntry>
  );
}
