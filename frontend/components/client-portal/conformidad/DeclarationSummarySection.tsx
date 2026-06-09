"use client";

/**
 * DeclarationSummarySection · responsible + scope.
 *
 * SAN-E v3.MB-5.6.D · admin pre-set responsible_person_* · cliente VE.
 */
import { Mail, User } from "lucide-react";

import type { ConformidadDeclarationClientView } from "@/lib/api/conformidad";


interface Props {
  declaration: ConformidadDeclarationClientView;
}


export function DeclarationSummarySection({ declaration }: Props) {
  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-[color:var(--fulkro-title)]">
        Responsable de la declaración
      </h2>

      <p className="mb-4 text-sm text-[color:var(--fulkro-muted)]">
        El responsable es quien aparecerá como firmante en el documento
        oficial. Marcos ya lo ha rellenado por ti · contacta si necesitas
        cambiarlo antes de firmar.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex items-start gap-3 rounded-md border bg-background px-3 py-3">
          <User className="mt-0.5 h-5 w-5 flex-shrink-0 text-fulkro-primary-700" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Nombre
            </p>
            <p className="mt-1 text-sm font-medium">
              {declaration.responsible_person_name || "Sin definir"}
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-md border bg-background px-3 py-3">
          <Mail className="mt-0.5 h-5 w-5 flex-shrink-0 text-fulkro-primary-700" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Email
            </p>
            {declaration.responsible_person_email ? (
              <a
                href={`mailto:${declaration.responsible_person_email}`}
                className="mt-1 block truncate text-sm font-medium text-fulkro-primary-700 hover:underline"
              >
                {declaration.responsible_person_email}
              </a>
            ) : (
              <p className="mt-1 text-sm font-medium">Sin definir</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
