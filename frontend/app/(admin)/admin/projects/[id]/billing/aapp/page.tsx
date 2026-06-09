import { AappBillingPanel } from "@/components/project/AappBillingPanel";

export default function AappBillingPage({
  params,
}: {
  params: { id: string };
}) {
  return <AappBillingPanel projectId={params.id} />;
}
