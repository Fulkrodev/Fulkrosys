"use client";

/**
 * TierAwareNextStepSection · explica qué pasa después de firmar.
 *
 * SAN-E v3.MB-5.6.D · next_step_post_signature backend driven · tier-aware.
 *
 * BASICA · distintivo + cert-id + publicación
 * MEDIA/ALTA · Marcos envía dossier ENAC · plazos 30-60 días
 */
import { Award, Calendar } from "lucide-react";

import type { ConformidadDeclarationClientView } from "@/lib/api/conformidad";


interface Props {
  declaration: ConformidadDeclarationClientView;
}


export function TierAwareNextStepSection({ declaration }: Props) {
  const isBasica = declaration.declaration_type === "initial";
  const Icon = isBasica ? Award : Calendar;

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-[color:var(--fulkro-title)]">
        <Icon className="h-5 w-5 text-fulkro-primary-700" />
        ¿Qué pasa después de firmar?
      </h2>

      <p className="mb-4 text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
        {declaration.next_step_post_signature}
      </p>

      {isBasica ? (
        <ul className="space-y-2 text-sm text-[color:var(--fulkro-muted)]">
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-fulkro-success" />
            <span>Generamos tu distintivo de conformidad en formato SVG</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-fulkro-success" />
            <span>Asignamos un cert-id único para tu certificación</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-fulkro-success" />
            <span>Descargas el documento oficial firmado en .docx</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-fulkro-success" />
            <span>
              Marcos te ayuda con la publicación URL evidence en el Registro
              CCN si aplica
            </span>
          </li>
        </ul>
      ) : (
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--fulkro-muted)]">
            Cronograma típico
          </p>
          {/* Hitos derivados de la prosa backend (next_step_post_signature ·
              fuente única m27 portal_api): firmar → Marcos envía dossier ·
              30-60 días certificación. Sin plazos intermedios inventados. */}
          <ol className="space-y-3 text-sm">
            <li className="flex items-start gap-3 rounded-md border bg-background px-3 py-2">
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-fulkro-primary-700 text-xs font-bold text-white">
                1
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">Ahora</p>
                <p className="text-xs text-[color:var(--fulkro-muted)]">
                  Firmas el compromiso · Marcos envía tu dossier al auditor
                  ENAC acreditado
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3 rounded-md border bg-background px-3 py-2">
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-fulkro-primary-700 text-xs font-bold text-white">
                2
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">30 a 60 días</p>
                <p className="text-xs text-[color:var(--fulkro-muted)]">
                  Auditoría formal · certificación final emitida por el
                  auditor ENAC
                </p>
              </div>
            </li>
          </ol>
        </div>
      )}
    </section>
  );
}
