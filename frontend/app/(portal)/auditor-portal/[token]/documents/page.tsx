import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DocumentsView } from "@/components/auditor-portal/views/DocumentsView";

export const metadata = { title: "Portal auditor · Documentos" };

export default async function AuditorPortalDocumentsPage(
  props: {
    params: Promise<{ token: string }>;
  }
) {
  const params = await props.params;
  return (
    <AuditorPortalEntry token={params.token}>
      <DocumentsView token={params.token} />
    </AuditorPortalEntry>
  );
}
