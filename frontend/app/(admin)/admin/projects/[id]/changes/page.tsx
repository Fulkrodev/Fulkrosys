import { ChangesList } from "@/components/m28_change_governance/ChangesList";

export default function ChangesPage({
  params,
}: {
  params: { id: string };
}) {
  return <ChangesList projectId={params.id} />;
}
