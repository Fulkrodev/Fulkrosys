import { DevHint } from "@/components/dev/DevHint";
import { PipelineKanban } from "@/components/pipeline/PipelineKanban";

export const metadata = {
  title: "Pipeline comercial · FULKRO",
};

export default function PipelinePage() {
  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
          Pipeline comercial
        </h1>
        <p className="text-base font-medium text-[color:var(--fulkro-body)]">
          Arrastra un lead entre columnas para actualizar su etapa. Pulsa
          para abrir el detalle lateral.{" "}
          <DevHint>Leads mock — /api/v1/leads pendiente en backend.</DevHint>
        </p>
      </header>

      <PipelineKanban />
    </div>
  );
}
