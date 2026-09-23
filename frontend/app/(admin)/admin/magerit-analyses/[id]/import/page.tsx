import { MageritImportPanel } from "@/components/project/MageritImportPanel";

export default async function MageritImportPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <MageritImportPanel analysisId={params.id} />;
}
