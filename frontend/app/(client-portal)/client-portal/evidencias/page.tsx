import { EvidenciasUploadPage } from "@/components/client-portal/EvidenciasUploadPage";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { PageContainer } from "@/components/layout/PageContainer";

export default function EvidenciasPage() {
  return (
    <PageContainer variant="app">
      <div className="space-y-4">
        <h1 className="mb-2 text-2xl font-bold">Evidencias</h1>
        <AgentSuggestionBanner
          slug="a27_clasificador_upload"
          pageUrl="/client-portal/evidencias"
          dismissKey="evidencias_classifier_dismissed"
        />
        <EvidenciasUploadPage />
      </div>
    </PageContainer>
  );
}
