import { ContractsList } from "@/components/m14_contracts/ContractsList";
import { SubcontractsPanel } from "@/components/m14_contracts/SubcontractsPanel";

export default function ContratosPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <ContractsList projectId={params.id} />
      <SubcontractsPanel projectId={params.id} />
    </div>
  );
}
