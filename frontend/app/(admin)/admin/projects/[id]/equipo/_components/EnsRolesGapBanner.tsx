"use client";

/**
 * EnsRolesGapBanner · sub-atom 1.C.F.4 v3.10.
 *
 * Banner top Tab Roles ENS · alerta Marcos cuando faltan asignaciones
 * críticas para la categoría del proyecto. Materializa R30 (admin tutor ·
 * Marcos asume cero ENS · banner explica qué falta y por qué importa).
 *
 * Lógica:
 *   - all_assigned === true · NO banner.
 *   - critical_missing.length > 0 · banner rojo "X críticos pendientes".
 *   - missing > 0 pero critical_missing === 0 · banner amarillo informativo.
 */
import { Badge } from "@/components/ui/badge";

import {
  ENS_ROLE_LABELS_FRONTEND,
  type EnsRequiredRolesStatus,
} from "@/lib/api/project-contacts";

type Props = {
  status: EnsRequiredRolesStatus;
};

export function EnsRolesGapBanner({ status }: Props) {
  if (status.all_assigned) {
    return null;
  }

  const criticalCount = status.critical_missing.length;
  const totalMissing = status.missing.length;
  const isCritical = criticalCount > 0;

  const tone = isCritical
    ? "border-fulkro-danger/40 bg-fulkro-danger/10 text-fulkro-danger"
    : "border-fulkro-warning/40 bg-fulkro-warning/10 text-fulkro-ink-700";

  const headline = isCritical
    ? `${criticalCount} rol${criticalCount === 1 ? "" : "es"} crítico${
        criticalCount === 1 ? "" : "s"
      } pendiente${criticalCount === 1 ? "" : "s"}`
    : `${totalMissing} rol${totalMissing === 1 ? "" : "es"} pendiente${
        totalMissing === 1 ? "" : "s"
      } asignar`;

  const rolesToList = isCritical ? status.critical_missing : status.missing;

  return (
    <div className={`rounded-md border px-4 py-3 ${tone}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold">
            {headline}
            {status.project_category ? (
              <span className="ml-2 text-xs font-normal">
                · Categoría {status.project_category}
              </span>
            ) : null}
          </p>
          <p className="text-xs">
            {isCritical
              ? "Sin estos roles no podrás auto-generar plantillas ENS firmadas (E-002 · E-012 · E-040 · E-041)."
              : "Roles opcionales según categoría · documentación más completa al asignarlos."}
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {rolesToList.map((role) => (
            <Badge key={role} variant={isCritical ? "danger" : "warning"}>
              {ENS_ROLE_LABELS_FRONTEND[role] ?? role}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}
