import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DdaEvidenceGapsView } from "@/components/auditor-portal/views/DdaEvidenceGapsView";

export const metadata = {
  title: "Portal auditor · Cobertura DdA-Evidencias",
};

export default function AuditorPortalGapsPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <DdaEvidenceGapsView token={params.token} />
    </AuditorPortalEntry>
  );
}
