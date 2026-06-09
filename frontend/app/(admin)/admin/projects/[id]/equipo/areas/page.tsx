"use client";

/**
 * /admin/projects/[id]/equipo/areas · sub-atom 1.C.F.2.2.
 *
 * Deep-link a la gestión completa de áreas (mismo contenido que el tab
 * Áreas dentro de /equipo/page.tsx). Útil para enlaces directos desde
 * el banner de sugerencias o desde emails internos.
 */
import Link from "next/link";

import { AreasPanel } from "../_components/AreasPanel";

export default function AreasPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          <Link
            href={`/admin/projects/${params.id}/equipo`}
            className="text-fulkro-primary-700 underline-offset-2 hover:underline"
          >
            ← Volver a Equipo
          </Link>
        </p>
        <h1 className="mt-2 text-2xl font-bold text-[color:var(--fulkro-title)]">
          Áreas / Departamentos
        </h1>
        <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
          Estructura organizativa del proyecto cliente. Adaptada per categoría
          ENS (R28): BÁSICA / MEDIA / ALTA.
        </p>
      </div>

      <AreasPanel projectId={params.id} />
    </div>
  );
}
