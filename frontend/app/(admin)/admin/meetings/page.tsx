/**
 * /admin/meetings — Listado meetings cross-cliente (sub-bloque 7.B.10).
 *
 * Vista global meetings con filtros + búsqueda FTS. Reuse
 * MeetingsHistoryTable component sin clientId filter (cross-cliente).
 */
"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Calendar, Plus, Search } from "lucide-react";

import {
  listMeetings,
  searchMeetings,
} from "@/lib/admin-meetings/api";
import {
  MEETING_STATUSES,
  PLATFORM_LABELS,
  STATUS_LABELS,
  type MeetingListItem,
  type MeetingStatus,
} from "@/lib/admin-meetings/schemas";

const STATUS_VARIANTS: Record<MeetingStatus, "default" | "secondary"> = {
  scheduled: "secondary",
  in_progress: "default",
  completed: "default",
  cancelled: "secondary",
};

export default function AdminMeetingsListPage() {
  const [items, setItems] = React.useState<MeetingListItem[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [statusFilter, setStatusFilter] = React.useState<MeetingStatus | "">("");
  const [searchQuery, setSearchQuery] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    async function fetch() {
      try {
        const data = await listMeetings({
          status: statusFilter || undefined,
          limit: 100,
        });
        if (!cancelled) {
          setItems(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error cargando reuniones");
        }
      }
    }
    void fetch();
    return () => {
      cancelled = true;
    };
  }, [statusFilter]);

  const filtered = React.useMemo(() => {
    if (!items) return null;
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (m) =>
        m.title.toLowerCase().includes(q) ||
        (m.interlocutor_name?.toLowerCase().includes(q) ?? false),
    );
  }, [items, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Calendar size={20} className="text-fulkro-primary-700" />
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
              Reuniones
            </h1>
            <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
              Listado cross-cliente · M_meetings (FASE 7)
            </p>
          </div>
        </div>
        <Link href="/admin/meetings/new">
          <Button type="button" size="sm">
            <Plus size={14} className="mr-1" />
            Nueva reunión
          </Button>
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-48 max-w-md">
          <Search
            size={14}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-fulkro-ink-400"
          />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filtrar por título o interlocutor…"
            className="pl-7"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) =>
            setStatusFilter(e.target.value as MeetingStatus | "")
          }
          className="rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
          aria-label="Filtrar por estado"
        >
          <option value="">Todos los estados</option>
          {MEETING_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {items === null ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : filtered && filtered.length === 0 ? (
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-6 text-center text-base font-medium text-[color:var(--fulkro-muted)]">
          No hay reuniones que mostrar.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Título</TableHead>
              <TableHead className="w-32">Fecha</TableHead>
              <TableHead className="w-28">Plataforma</TableHead>
              <TableHead className="w-24">Etapa K</TableHead>
              <TableHead>Interlocutor</TableHead>
              <TableHead className="w-28">Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered?.map((m) => (
              <TableRow
                key={m.id}
                className="cursor-pointer hover:bg-fulkro-ink-50"
              >
                <TableCell>
                  <Link
                    href={`/admin/meetings/${m.id}`}
                    className="font-medium text-fulkro-primary-700 hover:underline"
                  >
                    {m.title || "(sin título)"}
                  </Link>
                </TableCell>
                <TableCell className="text-xs text-fulkro-ink-600">
                  {m.meeting_date
                    ? new Date(m.meeting_date).toLocaleDateString("es-ES", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })
                    : "—"}
                </TableCell>
                <TableCell className="text-xs">
                  {m.platform ? PLATFORM_LABELS[m.platform] : "—"}
                </TableCell>
                <TableCell className="text-xs">{m.etapa_k ?? "—"}</TableCell>
                <TableCell className="text-xs">
                  {m.interlocutor_name ?? (
                    <span className="text-fulkro-ink-400">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANTS[m.status]}>
                    {STATUS_LABELS[m.status]}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
