/**
 * ConfirmConformidadFlow · #32 CONFIRMACION_CONFORMIDAD (FASE 4.5 B.2).
 *
 * Cliente confirma estado de conformidad ENS pre-auditoría ENAC. Scope:
 *   { porcentaje_implantacion?: number,
 *     medidas_implantadas?: number, total_medidas?: number,
 *     evidencias_recopiladas?: number,
 *     riesgos_aceptados?: number,
 *     no_conformidades_pendientes?: string[] }
 */
"use client";

import { CheckCircle2 } from "lucide-react";

import { BaseSignFlow } from "@/components/sign-flows/BaseSignFlow";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

interface ConformidadScope {
  porcentaje_implantacion?: number;
  medidas_implantadas?: number;
  total_medidas?: number;
  evidencias_recopiladas?: number;
  riesgos_aceptados?: number;
  no_conformidades_pendientes?: string[];
}

export function ConfirmConformidadFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as ConformidadScope;
  const pct = scope.porcentaje_implantacion;

  return (
    <BaseSignFlow
      token={token}
      status={status}
      title="Confirmación de conformidad pre-auditoría"
      icon={CheckCircle2}
      actionLabel="su confirmación del estado de conformidad pre-auditoría"
      legalNote="Conforme al Real Decreto 311/2022 (Esquema Nacional de Seguridad)."
      approveLabel="Confirmar conformidad"
      rejectLabel="Solicitar más tiempo"
      successMessage="Confirmación registrada. El expediente avanza hacia submission ENAC."
    >
      {typeof pct === "number" ? (
        <div className="rounded-md border border-fulkro-success/40 bg-fulkro-success/5 p-3">
          <p className="text-xs text-fulkro-success">Implantación SGSI</p>
          <p className="text-2xl font-semibold text-fulkro-success">{pct}%</p>
        </div>
      ) : null}
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 text-xs">
        <div>
          <dt className="text-fulkro-ink-500">Medidas Anexo II</dt>
          <dd className="font-semibold text-fulkro-ink-700">
            {scope.medidas_implantadas ?? "—"}
            {scope.total_medidas ? ` / ${scope.total_medidas}` : ""}
          </dd>
        </div>
        <div>
          <dt className="text-fulkro-ink-500">Evidencias</dt>
          <dd className="font-semibold text-fulkro-ink-700">
            {scope.evidencias_recopiladas ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-fulkro-ink-500">Riesgos aceptados</dt>
          <dd className="font-semibold text-fulkro-ink-700">
            {scope.riesgos_aceptados ?? "—"}
          </dd>
        </div>
      </dl>
      {scope.no_conformidades_pendientes &&
      scope.no_conformidades_pendientes.length > 0 ? (
        <div className="rounded-md border border-fulkro-warning/40 bg-fulkro-warning/5 p-3 text-xs text-fulkro-warning">
          <p className="font-semibold">No conformidades pendientes</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {scope.no_conformidades_pendientes.slice(0, 5).map((nc, idx) => (
              <li key={idx}>{nc}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </BaseSignFlow>
  );
}
