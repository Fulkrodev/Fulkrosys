/**
 * ApproveFacturaFlow · #26 APROBACION_FACTURA (FASE 4.5 sub-bloque B.2).
 *
 * Cliente revisa una factura F-### y la aprueba/solicita revisión antes
 * del envío oficial al circuito contable. Scope:
 *   { factura_codigo: string, importe?: string,
 *     conceptos?: Array<{ descripcion: string, importe?: string }> }
 */
"use client";

import { Receipt } from "lucide-react";

import { BaseSignFlow } from "@/components/sign-flows/BaseSignFlow";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

interface FacturaScope {
  factura_codigo?: string;
  importe?: string;
  conceptos?: Array<{ descripcion: string; importe?: string }>;
}

export function ApproveFacturaFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as FacturaScope;
  const codigo = scope.factura_codigo ?? "(sin código)";

  return (
    <BaseSignFlow
      token={token}
      status={status}
      title="Aprobación de factura"
      icon={Receipt}
      actionLabel="su aprobación de la factura"
      itemReference={scope.factura_codigo}
      approveLabel="Aprobar factura"
      rejectLabel="Solicitar revisión"
      successMessage="Aprobación registrada. La factura entra en circuito contable."
    >
      <div>
        <p className="text-xs font-mono text-fulkro-ink-500">{codigo}</p>
        {scope.importe ? (
          <p className="mt-1 text-base font-semibold text-fulkro-primary-700">
            Importe: {scope.importe}
          </p>
        ) : null}
      </div>
      {scope.conceptos && scope.conceptos.length > 0 ? (
        <div className="rounded-md border border-fulkro-ink-300/60 bg-white">
          <table aria-label="Detalle de la factura" className="w-full text-sm">
            <thead className="bg-fulkro-ink-100/40 text-xs">
              <tr>
                <th className="p-2 text-left font-medium">Concepto</th>
                <th className="p-2 text-right font-medium">Importe</th>
              </tr>
            </thead>
            <tbody>
              {scope.conceptos.slice(0, 8).map((c, idx) => (
                <tr key={idx} className="border-t border-fulkro-ink-300/40">
                  <td className="p-2">{c.descripcion}</td>
                  <td className="p-2 text-right font-mono">
                    {c.importe ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </BaseSignFlow>
  );
}
