"use client";

/**
 * DepartmentContactsList · sub-atom 1.C.F.3.2.
 *
 * Renderiza los empleados asignados a un área dada. Usado dentro de
 * `DepartmentEditModal` (sección informativa al editar) y opcionalmente
 * desde la fila de la tabla de áreas (popover preview).
 *
 * `reloadKey` permite forzar refetch tras un cambio externo.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import {
  listContactsForDepartment,
  type ContactSummaryForDepartment,
} from "@/lib/api/departments";
import { ROLE_CATEGORY_LABELS } from "@/lib/admin-contacts/schemas";

type Props = {
  projectId: string;
  departmentId: string;
  reloadKey?: number;
};

export function DepartmentContactsList({
  projectId,
  departmentId,
  reloadKey,
}: Props) {
  const [items, setItems] = useState<ContactSummaryForDepartment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listContactsForDepartment(projectId, departmentId)
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error cargando empleados del área";
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, departmentId, reloadKey]);

  if (loading) {
    return <Skeleton className="h-16 w-full" />;
  }

  if (items.length === 0) {
    return (
      <p className="rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 px-3 py-3 text-sm text-[color:var(--fulkro-muted)]">
        Sin empleados asignados a esta área todavía.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-fulkro-ink-50 rounded-md border border-fulkro-ink-100 bg-white text-sm">
      {items.map((c) => (
        <li
          key={c.id}
          className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
        >
          <div className="flex flex-col">
            <span className="font-medium text-fulkro-ink-800">
              {c.full_name}
            </span>
            <span className="text-xs text-[color:var(--fulkro-muted)]">
              {c.role_title} · {c.email}
            </span>
          </div>
          <Badge variant="outline">
            {ROLE_CATEGORY_LABELS[
              c.role_category as keyof typeof ROLE_CATEGORY_LABELS
            ] ?? c.role_category}
          </Badge>
        </li>
      ))}
    </ul>
  );
}
