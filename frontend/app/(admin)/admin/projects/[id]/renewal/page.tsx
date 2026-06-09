import { RenewalWarRoom } from "@/components/renewal/RenewalWarRoom";

export default function RenewalPage({
  params,
}: {
  params: { id: string };
}) {
  return <RenewalWarRoom projectId={params.id} />;
}
