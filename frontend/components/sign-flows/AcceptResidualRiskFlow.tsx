/**
 * AcceptResidualRiskFlow · #29 ACEPTACION_RIESGO_RESIDUAL (FASE 4.5 B.2).
 *
 * RSEG acepta riesgo residual MAGERIT v3 (firma vinculante sobre la
 * postura de seguridad declarada). Scope:
 *   { riesgo_codigo: string, descripcion_riesgo?: string,
 *     probabilidad?: "BAJA"|"MEDIA"|"ALTA"|"MUY_ALTA",
 *     impacto?: "BAJO"|"MEDIO"|"ALTO"|"MUY_ALTO",
 *     nivel_residual?: string,
 *     controles_aplicados?: string[] }
 */
"use client";

import { ShieldAlert } from "lucide-react";

import { BaseSignFlow } from "@/components/sign-flows/BaseSignFlow";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

interface ResidualRiskScope {
  riesgo_codigo?: string;
  descripcion_riesgo?: string;
  probabilidad?: string;
  impacto?: string;
  nivel_residual?: string;
  controles_aplicados?: string[];
}

export function AcceptResidualRiskFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as ResidualRiskScope;
  const codigo = scope.riesgo_codigo ?? "(sin código)";

  return (
    <BaseSignFlow
      token={token}
      status={status}
      title="Aceptación de riesgo residual"
      icon={ShieldAlert}
      actionLabel="su aceptación del riesgo residual"
      itemReference={scope.riesgo_codigo}
      legalNote="Conforme al Real Decreto 311/2022 (Esquema Nacional de Seguridad) y a la metodología MAGERIT v3."
      approveLabel="Aceptar riesgo"
      rejectLabel="Escalar"
      successMessage="Aceptación registrada en el expediente del análisis de riesgos."
    >
      <div>
        <p className="text-xs font-mono text-fulkro-ink-500">{codigo}</p>
        {scope.descripcion_riesgo ? (
          <p className="mt-1 text-sm text-fulkro-ink-700">
            {scope.descripcion_riesgo}
          </p>
        ) : null}
      </div>
      <dl className="grid grid-cols-3 gap-3 text-xs">
        <div>
          <dt className="text-fulkro-ink-500">Probabilidad</dt>
          <dd className="font-semibold text-fulkro-ink-700">
            {scope.probabilidad ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-fulkro-ink-500">Impacto</dt>
          <dd className="font-semibold text-fulkro-ink-700">
            {scope.impacto ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-fulkro-ink-500">Nivel residual</dt>
          <dd className="font-semibold text-fulkro-warning">
            {scope.nivel_residual ?? "—"}
          </dd>
        </div>
      </dl>
      {scope.controles_aplicados && scope.controles_aplicados.length > 0 ? (
        <div>
          <p className="text-xs font-medium text-fulkro-ink-700">
            Controles aplicados
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-fulkro-ink-700">
            {scope.controles_aplicados.slice(0, 8).map((c, idx) => (
              <li key={idx}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </BaseSignFlow>
  );
}
