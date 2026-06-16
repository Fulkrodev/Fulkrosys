"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import { listContacts } from "@/lib/admin-contacts/api";
import type {
  ClientContactListItem,
  RoleCategory,
} from "@/lib/admin-contacts/schemas";

type Props = {
  /** id del cliente cuyos contactos listar. */
  clientId: string;
  /** id del contacto seleccionado actualmente (controlled). */
  value: string | null;
  onChange: (contactId: string | null) => void;
  /** filtra a contactos con esta categoría (opcional). */
  filterByCategory?: RoleCategory;
  /** filtra a contactos con is_signatory=true (opcional). */
  filterBySignatory?: boolean;
  placeholder?: string;
  disabled?: boolean;
};

/**
 * Selector reutilizable de contactos M30. Pensado para A18 (interlocutor
 * reunión), M14 (signatario contrato) y M29 (destinatario mensajería)
 * en sub-bloque 5.5.F integraciones.
 *
 * Implementación minimal: Popover + Input filter + lista. Sustituible
 * por shadcn/ui Command si se añade al proyecto en futuras sub-fases.
 */
export function ContactQuickPicker({
  clientId,
  value,
  onChange,
  filterByCategory,
  filterBySignatory,
  placeholder = "Selecciona contacto…",
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<ClientContactListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    listContacts(clientId, {
      role_category: filterByCategory ?? null,
      is_signatory: filterBySignatory ?? null,
      is_active: true,
    })
      .then((res) => {
        if (!cancelled) setItems(res);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : err,
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, clientId, filterByCategory, filterBySignatory]);

  const selected = useMemo(
    () => items.find((c) => c.id === value) ?? null,
    [items, value],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.role_title.toLowerCase().includes(q),
    );
  }, [items, search]);

  return (
    <Popover open={open} onOpenChange={(next) => !disabled && setOpen(next)}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className="w-full justify-between"
          disabled={disabled}
        >
          <span className="truncate text-left">
            {selected
              ? `${selected.full_name} · ${selected.role_title}`
              : placeholder}
          </span>
          <span className="ml-2 text-sm font-medium text-[color:var(--fulkro-muted)]">▼</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[var(--radix-popover-trigger-width)] p-0"
      >
        <div className="border-b border-fulkro-ink-100 p-2">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar contacto…"
            className="h-8"
          />
        </div>
        <div className="max-h-64 overflow-y-auto">
          {loading ? (
            <div className="space-y-2 p-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="p-3 text-center text-base font-medium text-[color:var(--fulkro-muted)]">
              {items.length === 0
                ? "Sin contactos disponibles"
                : "Sin resultados"}
            </p>
          ) : (
            <ul className="py-1">
              {filtered.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(c.id);
                      setOpen(false);
                      setSearch("");
                    }}
                    className={
                      "flex w-full flex-col px-3 py-2 text-left transition hover:bg-fulkro-ink-50 " +
                      (value === c.id ? "bg-fulkro-ink-50/60" : "")
                    }
                  >
                    <span className="text-sm font-medium text-fulkro-ink-800">
                      {c.full_name}
                      {c.is_primary ? (
                        <span className="ml-1 text-xs text-fulkro-primary-700">
                          (principal)
                        </span>
                      ) : null}
                    </span>
                    <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                      {c.role_title} · {c.email}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        {value ? (
          <div className="border-t border-fulkro-ink-100 p-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full text-xs"
              onClick={() => {
                onChange(null);
                setOpen(false);
              }}
            >
              Limpiar selección
            </Button>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}
