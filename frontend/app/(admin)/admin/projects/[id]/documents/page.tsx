import { LegalTemplatesPanel } from "@/components/contracts/LegalTemplatesPanel";
import { DocumentationLevelsPanel } from "@/components/documents/DocumentationLevelsPanel";
import { ExcelTemplatesGrid } from "@/components/documents/ExcelTemplatesGrid";
import { IdmsWorkbench } from "@/components/documents/IdmsWorkbench";
import { RectoresGeneratorPanel } from "@/components/documents/RectoresGeneratorPanel";
import { IdmsAdminLayout } from "@/components/idms/IdmsAdminLayout";

export default function DocumentsPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="flex flex-col gap-4">
      {/* Sub-atom 1.C.G.A v3.10 · workbench full tree + upload + viewer + history */}
      <IdmsAdminLayout projectId={params.id} />
      {/* IdmsWorkbench existing preservado: stats + recent + expiring resumen */}
      <IdmsWorkbench projectId={params.id} />
      <DocumentationLevelsPanel />
      <RectoresGeneratorPanel projectId={params.id} />
      <LegalTemplatesPanel projectId={params.id} />
      <ExcelTemplatesGrid projectId={params.id} />
    </div>
  );
}
