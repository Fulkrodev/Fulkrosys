import { FinancialPanel } from "@/components/financial/FinancialPanel";
import { ImplementationPaymentsPanel } from "@/components/financial/ImplementationPaymentsPanel";

export default function FinancialPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <>
      <FinancialPanel projectId={params.id} />
      {/* #45 · vista cruzada avance × pagos */}
      <div className="mx-auto w-full max-w-6xl pb-8">
        <ImplementationPaymentsPanel projectId={params.id} />
      </div>
    </>
  );
}
