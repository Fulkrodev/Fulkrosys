"use client";

/**
 * DepartmentsList · sub-atom 1.C.F.2.2 + 1.C.F.3.2.
 *
 * Tabla CRUD project-scoped · acciones inline editar/eliminar via modals.
 * Suggestions banner se renderiza fuera (areas/page.tsx) cuando count=0.
 *
 * Sub-atom 1.C.F.3.2: badge con `total_contacts` per área (lazy desde
 * `getDepartmentReport`) · click "Editar" abre modal con sección de
 * empleados asignados via `DepartmentContactsList`.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { ApiError } from "@/lib/api";
import {
  deleteDepartment,
  getDepartmentReport,
  type Department,
} from "@/lib/api/departments";

import { DepartmentEditModal } from "./DepartmentEditModal";

type Props = {
  projectId: string;
  departments: Department[];
  onChanged: () => void;
  /** Permite al padre forzar refetch del report (bump value). */
  reportReloadKey?: number;
};

export function DepartmentsList({
  projectId,
  departments,
  onChanged,
  reportReloadKey,
}: Props) {
  const [editing, setEditing] = useState<Department | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    let cancelled = false;
    if (departments.length === 0) {
      setCounts({});
      return;
    }
    getDepartmentReport(projectId)
      .then((report) => {
        if (cancelled) return;
        const next: Record<string, number> = {};
        for (const d of report.departments) {
          next[d.department_id] = d.total_contacts;
        }
        setCounts(next);
      })
      .catch(() => {
        // Falla silente · no es crítico para el render principal.
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, departments, reportReloadKey]);

  const handleDelete = async (dept: Department) => {
    const ok = window.confirm(
      `¿Eliminar el área "${dept.code}"? Esta acción es irreversible.`,
    );
    if (!ok) return;
    try {
      await deleteDepartment(projectId, dept.id);
      toast.success("Área eliminada");
      onChanged();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error eliminando área";
      toast.error(msg);
    }
  };

  if (departments.length === 0) {
    return (
      <p className="rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 px-3 py-6 text-center text-sm text-[color:var(--fulkro-muted)]">
        Sin áreas todavía. Usa el banner de sugerencias o crea una manualmente.
      </p>
    );
  }

  return (
    <>
      <div className="rounded-md border border-fulkro-ink-100 bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-fulkro-ink-100 text-left text-xs uppercase tracking-wide text-fulkro-ink-500">
            <tr>
              <th className="px-3 py-2">Código</th>
              <th className="px-3 py-2">Nombre</th>
              <th className="px-3 py-2">Empleados</th>
              <th className="px-3 py-2">Descripción</th>
              <th className="px-3 py-2 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {departments.map((d) => (
              <tr
                key={d.id}
                className="border-b border-fulkro-ink-50 last:border-0 hover:bg-fulkro-ink-50/40"
              >
                <td className="px-3 py-2">
                  <Badge variant="outline">{d.code}</Badge>
                </td>
                <td className="px-3 py-2 font-medium text-fulkro-ink-800">
                  {d.name}
                </td>
                <td className="px-3 py-2 text-fulkro-ink-700">
                  <Badge variant="secondary">
                    {counts[d.id] ?? 0} empleado
                    {(counts[d.id] ?? 0) === 1 ? "" : "s"}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-fulkro-ink-700">
                  {d.description ?? "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setEditing(d)}
                  >
                    Editar
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => void handleDelete(d)}
                  >
                    Eliminar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <DepartmentEditModal
        projectId={projectId}
        department={editing}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null);
          onChanged();
        }}
      />
    </>
  );
}
