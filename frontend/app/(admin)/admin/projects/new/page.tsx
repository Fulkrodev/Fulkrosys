import { Suspense } from "react";

import { ProjectDiagnosticoWizard } from "@/components/project-wizard/ProjectDiagnosticoWizard";

export const metadata = {
  title: "Nuevo proyecto · Diagnóstico ENS · FULKRO",
};

export default function NewProjectPage() {
  // #7.5 · el wizard usa useSearchParams (lead_id) → frontera Suspense para
  // blindar el build estático (precedente oauth-callback).
  return (
    <Suspense fallback={null}>
      <ProjectDiagnosticoWizard />
    </Suspense>
  );
}
