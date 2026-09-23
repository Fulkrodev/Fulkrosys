import { ChangesList } from "@/components/m28_change_governance/ChangesList";

export default async function ChangesPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ChangesList projectId={params.id} />;
}
