import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { EvidenceView } from "@/components/auditor-portal/views/EvidenceView";

export const metadata = { title: "Portal auditor · Evidencias" };

export default function AuditorPortalEvidencePage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <EvidenceView token={params.token} />
    </AuditorPortalEntry>
  );
}
