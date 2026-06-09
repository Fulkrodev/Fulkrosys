/**
 * ValidateScopeChangeFlow · #28 VALIDACION_CAMBIO_ALCANCE (FASE 4.5 B.2).
 *
 * Cliente valida un cambio sobre el alcance original del proyecto (M28
 * Change Governance). Scope:
 *   { cambio_codigo: string, descripcion_cambio?: string,
 *     sistemas_afectados?: string[], impacto_estimado?: string }
 */
"use client";

import { GitBranch } from "lucide-react";

import { BaseSignFlow } from "@/components/sign-flows/BaseSignFlow";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

interface ScopeChangeScope {
  cambio_codigo?: string;
  descripcion_cambio?: string;
  sistemas_afectados?: string[];
  impacto_estimado?: string;
}

export function ValidateScopeChangeFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as ScopeChangeScope;
  const codigo = scope.cambio_codigo ?? "(sin código)";

  return (
    <BaseSignFlow
      token={token}
      status={status}
      title="Validación de cambio de alcance"
      icon={GitBranch}
      actionLabel="su validación del cambio de alcance"
      itemReference={scope.cambio_codigo}
      approveLabel="Validar cambio"
      rejectLabel="Rechazar"
      successMessage="Validación registrada. El cambio queda formalizado en el expediente."
    >
      <div>
        <p className="text-xs font-mono text-fulkro-ink-500">{codigo}</p>
        {scope.descripcion_cambio ? (
          <p className="mt-1 text-sm text-fulkro-ink-700">
            {scope.descripcion_cambio}
          </p>
        ) : null}
      </div>
      {scope.sistemas_afectados && scope.sistemas_afectados.length > 0 ? (
        <div>
          <p className="text-xs font-medium text-fulkro-ink-700">
            Sistemas afectados
          </p>
          <ul className="mt-1 flex flex-wrap gap-1.5">
            {scope.sistemas_afectados.map((s) => (
              <li
                key={s}
                className="rounded-full bg-fulkro-ink-100 px-2 py-0.5 text-xs text-fulkro-ink-700"
              >
                {s}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {scope.impacto_estimado ? (
        <div className="rounded-md border border-fulkro-warning/40 bg-fulkro-warning/5 p-3 text-xs text-fulkro-warning">
          <span className="font-semibold">Impacto estimado:</span>{" "}
          {scope.impacto_estimado}
        </div>
      ) : null}
    </BaseSignFlow>
  );
}
