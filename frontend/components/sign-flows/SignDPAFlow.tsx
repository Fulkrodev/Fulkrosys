/**
 * SignDPAFlow · #31 CONSENTIMIENTO_TRATAMIENTO_DATOS (FASE 4.5 B.2).
 *
 * Cliente firma el Acuerdo de Tratamiento de Datos (DPA · RGPD/LOPDGDD).
 * Scope:
 *   { dpa_version: string, fecha_efectiva?: string,
 *     categorias_datos?: string[], finalidades?: string[],
 *     duracion_tratamiento?: string, descarga_pdf_url?: string }
 */
"use client";

import { FileLock2 } from "lucide-react";

import { BaseSignFlow } from "@/components/sign-flows/BaseSignFlow";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

interface DPAScope {
  dpa_version?: string;
  fecha_efectiva?: string;
  categorias_datos?: string[];
  finalidades?: string[];
  duracion_tratamiento?: string;
  descarga_pdf_url?: string;
}

export function SignDPAFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as DPAScope;

  return (
    <BaseSignFlow
      token={token}
      status={status}
      title="Acuerdo de Tratamiento de Datos"
      icon={FileLock2}
      actionLabel="su consentimiento al Acuerdo de Tratamiento de Datos (DPA)"
      itemReference={scope.dpa_version}
      legalNote="Esta firma vincula a la organización conforme al Reglamento (UE) 2016/679 (RGPD) y a la Ley Orgánica 3/2018 (LOPDGDD)."
      approveLabel="Firmar DPA"
      rejectLabel="Rechazar"
      successMessage="DPA firmado. Recibirá una copia con timestamp por email."
    >
      <div className="space-y-1">
        {scope.dpa_version ? (
          <p className="text-xs font-mono text-fulkro-ink-500">
            Versión: {scope.dpa_version}
            {scope.fecha_efectiva ? ` · efectivo ${scope.fecha_efectiva}` : ""}
          </p>
        ) : null}
        {scope.duracion_tratamiento ? (
          <p className="text-sm text-fulkro-ink-700">
            <span className="font-medium">Duración: </span>
            {scope.duracion_tratamiento}
          </p>
        ) : null}
      </div>
      {scope.categorias_datos && scope.categorias_datos.length > 0 ? (
        <div>
          <p className="text-xs font-medium text-fulkro-ink-700">
            Categorías de datos tratadas
          </p>
          <ul className="mt-1 flex flex-wrap gap-1.5">
            {scope.categorias_datos.map((c) => (
              <li
                key={c}
                className="rounded-full bg-fulkro-ink-100 px-2 py-0.5 text-xs text-fulkro-ink-700"
              >
                {c}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {scope.finalidades && scope.finalidades.length > 0 ? (
        <div>
          <p className="text-xs font-medium text-fulkro-ink-700">
            Finalidades del tratamiento
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-fulkro-ink-700">
            {scope.finalidades.slice(0, 5).map((f, idx) => (
              <li key={idx}>{f}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {scope.descarga_pdf_url ? (
        <a
          href={scope.descarga_pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-fulkro-primary-600 underline"
        >
          Descargar texto completo del DPA (PDF)
        </a>
      ) : null}
    </BaseSignFlow>
  );
}
