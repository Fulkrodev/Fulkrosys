"use client";

/**
 * DepartmentReportPanel · sub-atom 1.C.F.3.2.
 *
 * Reporte resumido empleados per área. Muestra:
 *  - Counts per area (total + breakdown role_category).
 *  - Bucket "Sin asignar" si hay empleados sueltos.
 *  - Total empleados (excluye usuarios portal).
 *
 * Renderizado dentro de AreasPanel debajo de la tabla.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import {
  getDepartmentReport,
  type DepartmentReport,
} from "@/lib/api/departments";
import { ROLE_CATEGORY_LABELS } from "@/lib/admin-contacts/schemas";

type Props = {
  projectId: string;
  reloadKey?: number;
};

function renderBreakdown(byCategory: Record<string, number>) {
  const entries = Object.entries(byCategory);
  if (entries.length === 0) {
    return (
      <span className="text-xs text-[color:var(--fulkro-muted)]">
        —
      </span>
    );
  }
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([cat, count]) => (
        <Badge key={cat} variant="outline" className="text-xs">
          {ROLE_CATEGORY_LABELS[
            cat as keyof typeof ROLE_CATEGORY_LABELS
          ] ?? cat}
          : {count}
        </Badge>
      ))}
    </div>
  );
}

export function DepartmentReportPanel({ projectId, reloadKey }: Props) {
  const [report, setReport] = useState<DepartmentReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDepartmentReport(projectId)
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error cargando reporte de áreas";
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, reloadKey]);

  if (loading) {
    return <Skeleton className="h-32 w-full" />;
  }

  if (!report) {
    return null;
  }

  const hasUnassigned = report.unassigned.total_contacts > 0;

  return (
    <div className="flex flex-col gap-3 rounded-md border border-fulkro-ink-100 bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-fulkro-ink-800">
          Empleados por área
        </h3>
        <Badge variant="secondary">
          {report.total_employees} empleado
          {report.total_employees === 1 ? "" : "s"}
        </Badge>
      </div>

      {report.departments.length === 0 && !hasUnassigned ? (
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          Aún no hay empleados ni áreas configuradas.
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-fulkro-ink-100 text-left text-xs uppercase tracking-wide text-fulkro-ink-500">
            <tr>
              <th className="px-2 py-1">Área</th>
              <th className="px-2 py-1">Total</th>
              <th className="px-2 py-1">Categorías</th>
            </tr>
          </thead>
          <tbody>
            {report.departments.map((d) => (
              <tr
                key={d.department_id}
                className="border-b border-fulkro-ink-50 last:border-0"
              >
                <td className="px-2 py-2">
                  <Badge variant="outline">{d.code}</Badge>
                  <span className="ml-2 text-fulkro-ink-700">{d.name}</span>
                </td>
                <td className="px-2 py-2 text-fulkro-ink-800">
                  {d.total_contacts}
                </td>
                <td className="px-2 py-2">
                  {renderBreakdown(d.by_role_category)}
                </td>
              </tr>
            ))}
            {hasUnassigned ? (
              <tr className="border-b border-fulkro-ink-50 last:border-0 bg-fulkro-ink-50/40">
                <td className="px-2 py-2 italic text-fulkro-ink-700">
                  Sin asignar
                </td>
                <td className="px-2 py-2 text-fulkro-ink-800">
                  {report.unassigned.total_contacts}
                </td>
                <td className="px-2 py-2">
                  {renderBreakdown(report.unassigned.by_role_category)}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      )}
    </div>
  );
}
