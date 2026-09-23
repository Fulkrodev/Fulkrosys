import { ContractsList } from "@/components/m14_contracts/ContractsList";
import { SubcontractsPanel } from "@/components/m14_contracts/SubcontractsPanel";

export default async function ContratosPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return (
    <div className="space-y-6">
      <ContractsList projectId={params.id} />
      <SubcontractsPanel projectId={params.id} />
    </div>
  );
}
