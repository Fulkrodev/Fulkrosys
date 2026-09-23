import { redirect } from "next/navigation";

export default async function ProjectIndex(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  redirect(`/admin/projects/${params.id}/summary`);
}
