import { ExitChecklist } from "@/components/exit/ExitChecklist";

export default async function ExitPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <ExitChecklist projectId={params.id} />;
}
