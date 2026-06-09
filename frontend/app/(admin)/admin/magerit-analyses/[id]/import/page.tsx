import { MageritImportPanel } from "@/components/project/MageritImportPanel";

export default function MageritImportPage({
  params,
}: {
  params: { id: string };
}) {
  return <MageritImportPanel analysisId={params.id} />;
}
