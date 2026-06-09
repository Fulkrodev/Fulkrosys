import { CopilotMemoryWorkspace } from "@/components/agents/CopilotMemoryWorkspace";

export const metadata = {
  title: "Copiloto · FULKRO",
};

export default function CopilotPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <header>
        <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
          Copiloto FULKRO
        </h1>
        <p className="text-base font-medium text-[color:var(--fulkro-body)]">
          Memoria por proyecto · cada conversación queda guardada y el copiloto
          recuerda lo que hablasteis. Citas normativas del Agente 14.
        </p>
      </header>

      <CopilotMemoryWorkspace />
    </div>
  );
}
