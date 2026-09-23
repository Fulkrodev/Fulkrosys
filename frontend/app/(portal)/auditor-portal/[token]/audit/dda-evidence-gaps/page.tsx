import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DdaEvidenceGapsView } from "@/components/auditor-portal/views/DdaEvidenceGapsView";

export const metadata = {
  title: "Portal auditor · Cobertura DdA-Evidencias",
};

export default async function AuditorPortalGapsPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <DdaEvidenceGapsView token={params.token} />
    </AuditorPortalEntry>
  );
}
