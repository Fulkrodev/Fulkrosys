import { AdminTransparencyView } from "@/components/transparency/AdminTransparencyView";

export default function ProjectTransparencyPage({
  params,
}: {
  params: { id: string };
}) {
  return <AdminTransparencyView projectId={params.id} />;
}
