import { EvidenciasUploadPage } from "@/components/client-portal/EvidenciasUploadPage";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";

export default function EvidenciasPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-8 space-y-4">
      <h1 className="mb-2 text-2xl font-bold">Evidencias</h1>
      <AgentSuggestionBanner
        slug="a27_clasificador_upload"
        pageUrl="/client-portal/evidencias"
        dismissKey="evidencias_classifier_dismissed"
      />
      <EvidenciasUploadPage />
    </main>
  );
}
