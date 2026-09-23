import { AappBillingPanel } from "@/components/project/AappBillingPanel";

export default async function AappBillingPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <AappBillingPanel projectId={params.id} />;
}
