import { ExitChecklist } from "@/components/exit/ExitChecklist";

export default function ExitPage({
  params,
}: {
  params: { id: string };
}) {
  return <ExitChecklist projectId={params.id} />;
}
