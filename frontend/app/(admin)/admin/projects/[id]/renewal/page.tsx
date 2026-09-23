import { RenewalWarRoom } from "@/components/renewal/RenewalWarRoom";

export default async function RenewalPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <RenewalWarRoom projectId={params.id} />;
}
