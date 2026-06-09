import { redirect } from "next/navigation";

export default function ProjectIndex({
  params,
}: {
  params: { id: string };
}) {
  redirect(`/admin/projects/${params.id}/summary`);
}
