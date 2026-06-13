import { RemediationConsolePanel } from "@/components/remediation/RemediationConsolePanel";

export default function ProjectRemediationPage({
  params,
}: {
  params: { id: string };
}) {
  return <RemediationConsolePanel projectId={params.id} />;
}
