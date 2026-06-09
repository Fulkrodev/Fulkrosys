import { AuditorPortalEntry } from "@/components/auditor-portal/AuditorPortalEntry";
import { DocumentsView } from "@/components/auditor-portal/views/DocumentsView";

export const metadata = { title: "Portal auditor · Documentos" };

export default function AuditorPortalDocumentsPage({
  params,
}: {
  params: { token: string };
}) {
  return (
    <AuditorPortalEntry token={params.token}>
      <DocumentsView token={params.token} />
    </AuditorPortalEntry>
  );
}
