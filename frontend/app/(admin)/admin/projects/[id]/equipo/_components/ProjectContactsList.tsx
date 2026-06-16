"use client";

/**
 * ProjectContactsList · sub-atom 1.C.F.1 + 1.C.F.3.2.
 *
 * DataTable contactos project-scoped (m30 project_scope_api). Filter
 * has_portal_access para tabs Usuarios / Empleados.
 *
 * Sub-atom 1.C.F.3.2: columna "Departamento" en modo `employees` ·
 * dropdown inline asigna/des-asigna empleados a áreas vía
 * ContactDepartmentAssignSelect.
 */
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import {
  deleteProjectContact,
  listProjectContacts,
  type ProjectContact,
} from "@/lib/api/project-contacts";
import {
  listDepartments,
  type Department,
} from "@/lib/api/departments";
import { ROLE_CATEGORY_LABELS } from "@/lib/admin-contacts/schemas";

import { ContactDepartmentAssignSelect } from "./ContactDepartmentAssignSelect";

type Props = {
  projectId: string;
  reloadKey?: number;
  filter: "portal" | "employees";
  onReload: () => void;
  /** Notifica al padre que un assignment cambió (refresca reports). */
  onAssignmentChanged?: () => void;
};

export function ProjectContactsList({
  projectId,
  reloadKey,
  filter,
  onReload,
  onAssignmentChanged,
}: Props) {
  const [items, setItems] = useState<ProjectContact[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const showDepartments = filter === "employees";

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const tasks: Promise<unknown>[] = [
      listProjectContacts(projectId).then((res) => {
        if (!cancelled) setItems(res.contacts);
      }),
    ];
    if (showDepartments) {
      tasks.push(
        listDepartments(projectId).then((d) => {
          if (!cancelled) setDepartments(d);
        }),
      );
    }
    Promise.all(tasks)
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error cargando contactos del proyecto";
        setError(msg);
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, reloadKey, showDepartments]);

  const handleAssignmentChanged = (
    contactId: string,
    nextDepartmentId: string | null,
  ) => {
    setItems((prev) =>
      prev.map((c) =>
        c.id === contactId ? { ...c, department_id: nextDepartmentId } : c,
      ),
    );
    onAssignmentChanged?.();
  };

  const filtered = useMemo(() => {
    const filteredByPortal = items.filter((c) =>
      filter === "portal" ? c.has_portal_access : !c.has_portal_access,
    );
    if (!search.trim()) return filteredByPortal;
    const q = search.trim().toLowerCase();
    return filteredByPortal.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.role_title.toLowerCase().includes(q),
    );
  }, [items, filter, search]);

  const handleDelete = async (contactId: string) => {
    const ok = window.confirm(
      "¿Eliminar este contacto del proyecto? (soft delete · recuperable por DB)",
    );
    if (!ok) return;
    try {
      await deleteProjectContact(projectId, contactId);
      toast.success("Contacto eliminado");
      onReload();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error eliminando contacto";
      toast.error(msg);
    }
  };

  if (loading) {
    return <Skeleton className="h-24 w-full" />;
  }

  if (error) {
    return (
      <p className="rounded-md border border-fulkro-danger/40 bg-fulkro-danger/10 px-3 py-2 text-sm text-fulkro-danger">
        {error}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Buscar por nombre, email o cargo…"
        className="h-9 max-w-sm"
      />

      <div className="rounded-md border border-fulkro-ink-100 bg-white">
        <table aria-label="Contactos del proyecto" className="w-full text-sm">
          <thead className="border-b border-fulkro-ink-100 text-left text-xs uppercase tracking-wide text-fulkro-ink-500">
            <tr>
              <th className="px-3 py-2">Nombre</th>
              <th className="px-3 py-2">Cargo</th>
              <th className="px-3 py-2">Categoría</th>
              <th className="px-3 py-2">Email</th>
              {showDepartments ? (
                <th className="px-3 py-2">Departamento</th>
              ) : null}
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2 text-right">Acción</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={showDepartments ? 7 : 6}
                  className="px-3 py-6 text-center text-base font-medium text-[color:var(--fulkro-muted)]"
                >
                  {filter === "portal"
                    ? "No hay usuario portal aún. Usa el panel superior."
                    : "Sin empleados aún. Añade el primero arriba."}
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-fulkro-ink-50 last:border-0 hover:bg-fulkro-ink-50/40"
                >
                  <td className="px-3 py-2 font-medium text-fulkro-ink-800">
                    {c.full_name}
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-700">
                    {c.role_title}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant="outline">
                      {ROLE_CATEGORY_LABELS[
                        c.role_category as keyof typeof ROLE_CATEGORY_LABELS
                      ] ?? c.role_category}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-700">{c.email}</td>
                  {showDepartments ? (
                    <td className="px-3 py-2">
                      <ContactDepartmentAssignSelect
                        projectId={projectId}
                        contactId={c.id}
                        currentDepartmentId={c.department_id ?? null}
                        departments={departments}
                        onChanged={(next) =>
                          handleAssignmentChanged(c.id, next)
                        }
                      />
                    </td>
                  ) : null}
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {c.is_primary ? (
                        <Badge variant="default">PRIMARY</Badge>
                      ) : null}
                      {c.is_signatory ? (
                        <Badge variant="secondary">SIGNATORY</Badge>
                      ) : null}
                      {c.has_portal_access ? (
                        <Badge variant="outline">PORTAL</Badge>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => void handleDelete(c.id)}
                    >
                      Eliminar
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {filtered.length > 0 ? (
        <div className="text-sm font-medium text-[color:var(--fulkro-muted)]">
          {filtered.length} {filter === "portal" ? "usuario" : "empleado"}
          {filtered.length === 1 ? "" : "s"}
        </div>
      ) : null}
    </div>
  );
}
