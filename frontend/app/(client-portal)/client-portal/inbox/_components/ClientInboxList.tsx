/**
 * ClientInboxList — listado threads del cliente (sub-bloque 6.B.1).
 *
 * - Tabla simple con summary thread (subject excerpt + last sender +
 *   fecha + unread badge + has_attachments icon)
 * - Filter chips: Todos / No leídos / Con archivos
 * - Polling 15s (refresca lista + unread count)
 * - Click row → onSelectThread(thread_id) (parent maneja Sheet o nav)
 *
 * Pattern coherente con admin-clients DataTable (sub-fase 5.A).
 */
"use client";

import { Paperclip } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

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

import { listInboxThreads } from "@/lib/client-messages/api";
import type { InboxFilter, ThreadSummary } from "@/lib/client-messages/schemas";

interface ClientInboxListProps {
  onSelectThread: (threadId: string) => void;
  pollingIntervalMs?: number;
}

const FILTER_LABELS: Record<InboxFilter, string> = {
  all: "Todos",
  unread: "No leídos",
  with_attachments: "Con archivos",
};

export function ClientInboxList({
  onSelectThread,
  pollingIntervalMs = 15_000,
}: ClientInboxListProps) {
  const [threads, setThreads] = useState<ThreadSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<InboxFilter>("all");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function fetchThreads() {
      try {
        const data = await listInboxThreads();
        if (!cancelled) {
          setThreads(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error cargando bandeja");
        }
      }
    }

    void fetchThreads();
    if (pollingIntervalMs > 0) {
      timer = setInterval(fetchThreads, pollingIntervalMs);
    }
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [pollingIntervalMs]);

  const filtered = useMemo(() => {
    if (!threads) return null;
    if (filter === "unread") {
      return threads.filter((t) => t.unread_for_client > 0);
    }
    if (filter === "with_attachments") {
      return threads.filter((t) => t.has_attachments);
    }
    return threads;
  }, [threads, filter]);

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Error: {error}
      </div>
    );
  }

  if (threads === null) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filtros">
        {(Object.keys(FILTER_LABELS) as InboxFilter[]).map((f) => (
          <Button
            key={f}
            type="button"
            size="sm"
            variant={filter === f ? "primary" : "outline"}
            onClick={() => setFilter(f)}
            role="tab"
            aria-selected={filter === f}
          >
            {FILTER_LABELS[f]}
          </Button>
        ))}
      </div>

      {filtered && filtered.length === 0 ? (
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-6 text-center text-sm text-fulkro-ink-500">
          No hay mensajes que mostrar.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Resumen</TableHead>
              <TableHead className="w-32">Último</TableHead>
              <TableHead className="w-24 text-center">Mensajes</TableHead>
              <TableHead className="w-24 text-center">No leídos</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered?.map((t) => {
              const date = new Date(t.last_message_at);
              return (
                <TableRow
                  key={t.thread_id}
                  className="cursor-pointer hover:bg-fulkro-ink-50"
                  onClick={() => onSelectThread(t.thread_id)}
                  role="button"
                >
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <span className="line-clamp-2 text-sm">
                        {t.last_message_excerpt}
                      </span>
                      <span className="text-xs text-fulkro-ink-500">
                        Último de:{" "}
                        {t.last_message_from_role === "admin"
                          ? "Marcos"
                          : "Tú"}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-fulkro-ink-600">
                    {date.toLocaleDateString("es-ES", {
                      day: "2-digit",
                      month: "short",
                    })}
                  </TableCell>
                  <TableCell className="text-center">
                    {t.total_messages}
                  </TableCell>
                  <TableCell className="text-center">
                    {t.unread_for_client > 0 ? (
                      <Badge variant="default">{t.unread_for_client}</Badge>
                    ) : (
                      <span className="text-xs text-fulkro-ink-400">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    {t.has_attachments && (
                      <Paperclip
                        size={14}
                        className="text-fulkro-ink-500"
                        aria-label="Tiene adjuntos"
                      />
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
