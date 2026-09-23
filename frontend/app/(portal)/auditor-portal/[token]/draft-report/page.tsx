import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DraftReportView } from "@/components/auditor-portal/views/DraftReportView";

export const metadata = {
  title: "Portal auditor · Borrador del informe",
};

export default async function AuditorPortalDraftReportPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <DraftReportView token={params.token} />
    </AuditorPortalEntry>
  );
}
