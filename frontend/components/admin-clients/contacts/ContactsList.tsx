"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import { listContacts } from "@/lib/admin-contacts/api";
import type {
  ClientContactListItem,
  ListContactsFilters,
  RoleCategory,
} from "@/lib/admin-contacts/schemas";
import {
  ROLE_CATEGORIES,
  ROLE_CATEGORY_LABELS,
} from "@/lib/admin-contacts/schemas";

type Props = {
  clientId: string;
  reloadKey?: number;
  onRowSelect: (contactId: string) => void;
};

const ACTIVE_FILTERS = [
  { label: "Activos", value: true },
  { label: "Inactivos", value: false },
  { label: "Todos", value: null },
] as const;

function formatRelativeDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function ContactsList({ clientId, reloadKey, onRowSelect }: Props) {
  const [items, setItems] = useState<ClientContactListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeFilter, setActiveFilter] = useState<boolean | null>(true);
  const [categoryFilter, setCategoryFilter] = useState<RoleCategory | "all">(
    "all",
  );
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search 300ms.
  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const filters: ListContactsFilters = useMemo(
    () => ({
      is_active: activeFilter,
      role_category: categoryFilter === "all" ? null : categoryFilter,
      search: debouncedSearch || null,
    }),
    [activeFilter, categoryFilter, debouncedSearch],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listContacts(clientId, filters)
      .then((res) => {
        if (!cancelled) setItems(res);
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error cargando contactos";
        setError(msg);
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, filters, reloadKey]);

  return (
    <div className="flex flex-col gap-4">
      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-full border border-fulkro-ink-100 bg-white p-1">
          {ACTIVE_FILTERS.map((f) => (
            <button
              key={String(f.value)}
              type="button"
              onClick={() => setActiveFilter(f.value)}
              className={
                "rounded-full px-3 py-1 text-xs font-medium transition " +
                (activeFilter === f.value
                  ? "bg-fulkro-primary-700 text-white"
                  : "text-fulkro-ink-700 hover:bg-fulkro-ink-50")
              }
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* El nombre accesible va en `aria-label` y no en un <label> visible
            porque la primera opción («Todas las categorías») ya dice de qué es
            el desplegable a quien lo ve; quien lo recorre con un lector de
            pantalla llega al control sin ese contexto y necesita el nombre.
            Sin esto, axe lo marca como `select-name`, de severidad crítica. */}
        <select
          aria-label="Filtrar contactos por categoría de rol"
          value={categoryFilter}
          onChange={(e) =>
            setCategoryFilter(e.target.value as RoleCategory | "all")
          }
          className="h-9 rounded-md border border-fulkro-ink-200 bg-white px-2 text-sm"
        >
          <option value="all">Todas las categorías</option>
          {ROLE_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {ROLE_CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>

        {/* Un `placeholder` NO es una etiqueta: desaparece en cuanto se
            escribe, y un lector de pantalla no lo anuncia como nombre del
            campo. Era la violación `label`, también crítica. */}
        <Input
          aria-label="Buscar contactos por nombre, email o cargo"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, email o cargo…"
          className="h-9 max-w-xs"
        />
      </div>

      {/* Table */}
      <div className="rounded-md border border-fulkro-ink-100 bg-white">
        <table aria-label="Contactos del cliente" className="w-full text-sm">
          <thead className="border-b border-fulkro-ink-100 text-left text-xs uppercase tracking-wide text-fulkro-ink-500">
            <tr>
              <th className="px-3 py-2">Nombre</th>
              <th className="px-3 py-2">Cargo</th>
              <th className="px-3 py-2">Categoría</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Roles</th>
              <th className="px-3 py-2">Última interacción</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="p-3">
                  <Skeleton className="h-8 w-full" />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-3 py-6 text-center text-base font-medium text-[color:var(--fulkro-muted)]"
                >
                  {error
                    ? error
                    : "No hay contactos. Crea uno con \"Nuevo contacto\"."}
                </td>
              </tr>
            ) : (
              items.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => onRowSelect(c.id)}
                  className="cursor-pointer border-b border-fulkro-ink-50 last:border-0 hover:bg-fulkro-ink-50/40"
                >
                  <td className="px-3 py-2 font-medium text-fulkro-ink-800">
                    {c.full_name}
                    {c.preferred_name ? (
                      <span className="ml-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                        ({c.preferred_name})
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-700">
                    {c.role_title}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant="outline">
                      {ROLE_CATEGORY_LABELS[
                        c.role_category as RoleCategory
                      ] ?? c.role_category}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-fulkro-ink-700">
                    {c.email}
                  </td>
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
                      {!c.is_active ? (
                        <Badge variant="outline" className="text-fulkro-danger">
                          Inactivo
                        </Badge>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
                    {formatRelativeDate(c.last_interaction_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!loading && items.length > 0 ? (
        <div className="text-sm font-medium text-[color:var(--fulkro-muted)]">
          {items.length} contacto{items.length === 1 ? "" : "s"} listado
          {items.length === 1 ? "" : "s"}.
        </div>
      ) : null}

      {error ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setSearch((s) => s)}
        >
          Reintentar
        </Button>
      ) : null}
    </div>
  );
}
