/**
 * ApprovePropuestaFlow · #25 APROBACION_PROPUESTA (FASE 4.5 sub-bloque B.2).
 *
 * Cliente revisa una propuesta P-### y la aprueba/rechaza antes de pasar
 * al contrato C-001. Scope esperado:
 *   { propuesta_codigo: string, importe_total?: string, condiciones?: string[] }
 */
"use client";

import { ClipboardCheck } from "lucide-react";

import { BaseSignFlow } from "@/components/sign-flows/BaseSignFlow";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

interface PropuestaScope {
  propuesta_codigo?: string;
  importe_total?: string;
  condiciones?: string[];
}

export function ApprovePropuestaFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as PropuestaScope;
  const codigo = scope.propuesta_codigo ?? "(sin código)";

  return (
    <BaseSignFlow
      token={token}
      status={status}
      title="Aprobación de propuesta"
      icon={ClipboardCheck}
      actionLabel="su aprobación de la propuesta"
      itemReference={scope.propuesta_codigo}
      approveLabel="Aprobar propuesta"
      rejectLabel="Rechazar"
      successMessage="Aprobación registrada. Recibirá copia firmada por email."
    >
      <div>
        <p className="text-xs font-mono text-fulkro-ink-500">{codigo}</p>
        {scope.importe_total ? (
          <p className="mt-1 text-base font-semibold text-fulkro-primary-700">
            Importe total: {scope.importe_total}
          </p>
        ) : null}
      </div>
      {scope.condiciones && scope.condiciones.length > 0 ? (
        <div>
          <p className="text-xs font-medium text-fulkro-ink-700">
            Condiciones clave
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-fulkro-ink-700">
            {scope.condiciones.slice(0, 5).map((c, idx) => (
              <li key={idx}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </BaseSignFlow>
  );
}
