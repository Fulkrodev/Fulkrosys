import { BiaPanel } from "@/components/project/BiaPanel";
import { ContinuidadBuzonAdminPanel } from "@/components/project/ContinuidadBuzonAdminPanel";

export default function BiaPage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-6">
      <BiaPanel projectId={params.id} />
      {/* feat/fulkro-100 Ola A · buzón de continuidad del cliente + aviso borrador listo */}
      <ContinuidadBuzonAdminPanel projectId={params.id} />
    </div>
  );
}
