"use client";

/**
 * MeetingsHistoryTable — vista histórica meetings de un cliente
 * (sub-bloque 7.B.8 FASE 7).
 *
 * - Reusable: prop clientId
 * - Filter por status + filter por etapa K
 * - Click row → /admin/meetings/{id}
 * - Empty state si 0 reuniones
 */
import { ExternalLink, Plus } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
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
import { getMeetingsByClient } from "@/lib/admin-meetings/api";
import {
  ETAPA_K_LABELS,
  PLATFORM_LABELS,
  STATUS_LABELS,
  type MeetingEtapaK,
  type MeetingListItem,
  type MeetingStatus,
} from "@/lib/admin-meetings/schemas";

interface MeetingsHistoryTableProps {
  clientId: string;
  pollingIntervalMs?: number;
}

const STATUS_VARIANTS: Record<MeetingStatus, "default" | "secondary"> = {
  scheduled: "secondary",
  in_progress: "default",
  completed: "default",
  cancelled: "secondary",
};

export function MeetingsHistoryTable({
  clientId,
  pollingIntervalMs = 0,
}: MeetingsHistoryTableProps) {
  const [items, setItems] = React.useState<MeetingListItem[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [statusFilter, setStatusFilter] = React.useState<MeetingStatus | "">("");
  const [etapaFilter, setEtapaFilter] = React.useState<MeetingEtapaK | "">("");

  React.useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function fetch() {
      try {
        const data = await getMeetingsByClient(clientId);
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
    if (pollingIntervalMs > 0) {
      timer = setInterval(fetch, pollingIntervalMs);
    }
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [clientId, pollingIntervalMs]);

  const filtered = React.useMemo(() => {
    if (!items) return null;
    return items.filter((m) => {
      if (statusFilter && m.status !== statusFilter) return false;
      if (etapaFilter && m.etapa_k !== etapaFilter) return false;
      return true;
    });
  }, [items, statusFilter, etapaFilter]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as MeetingStatus | "")
            }
            className="rounded-md border border-fulkro-ink-300 px-2 py-1 text-sm"
            aria-label="Filtrar por estado"
          >
            <option value="">Todos los estados</option>
            {(Object.keys(STATUS_LABELS) as MeetingStatus[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          <select
            value={etapaFilter}
            onChange={(e) =>
              setEtapaFilter(e.target.value as MeetingEtapaK | "")
            }
            className="rounded-md border border-fulkro-ink-300 px-2 py-1 text-sm"
            aria-label="Filtrar por etapa K"
          >
            <option value="">Todas las etapas</option>
            {(Object.keys(ETAPA_K_LABELS) as MeetingEtapaK[]).map((e) => (
              <option key={e} value={e}>
                {ETAPA_K_LABELS[e]}
              </option>
            ))}
          </select>
        </div>
        <Link
          href={`/admin/meetings/new?client_id=${clientId}`}
          aria-label="Nueva reunión para este cliente"
        >
          <Button type="button" size="sm">
            <Plus size={14} className="mr-1" />
            Nueva reunión
          </Button>
        </Link>
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
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-6 text-center text-sm text-fulkro-ink-500">
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
              <TableHead className="w-20 text-center">Min</TableHead>
              <TableHead className="w-28">Estado</TableHead>
              <TableHead className="w-12"></TableHead>
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
                    {m.has_notes && (
                      <span className="ml-2 text-xs text-fulkro-ink-500">
                        · con notas
                      </span>
                    )}
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
                <TableCell className="text-xs">
                  {m.etapa_k ?? "—"}
                </TableCell>
                <TableCell className="text-xs">
                  {m.interlocutor_name ?? (
                    <span className="text-fulkro-ink-400">—</span>
                  )}
                </TableCell>
                <TableCell className="text-center text-xs">
                  {m.duration_minutes ?? "—"}
                </TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANTS[m.status]}>
                    {STATUS_LABELS[m.status]}
                  </Badge>
                </TableCell>
                <TableCell className="text-center">
                  <Link
                    href={`/admin/meetings/${m.id}`}
                    aria-label="Abrir detalle reunión"
                  >
                    <ExternalLink
                      size={14}
                      className="text-fulkro-ink-500"
                    />
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
