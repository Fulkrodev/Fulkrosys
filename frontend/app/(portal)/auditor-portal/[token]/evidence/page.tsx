import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { EvidenceView } from "@/components/auditor-portal/views/EvidenceView";

export const metadata = { title: "Portal auditor · Evidencias" };

export default async function AuditorPortalEvidencePage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <EvidenceView token={params.token} />
    </AuditorPortalEntry>
  );
}
