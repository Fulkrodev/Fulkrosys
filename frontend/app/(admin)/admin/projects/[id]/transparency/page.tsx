import { AdminTransparencyView } from "@/components/transparency/AdminTransparencyView";

export default async function ProjectTransparencyPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <AdminTransparencyView projectId={params.id} />;
}
