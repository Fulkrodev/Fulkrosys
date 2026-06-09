/**
 * AdminInboxList — bandeja admin cross-cliente (sub-bloque 6.B.2).
 *
 * Vista admin con prop opcional `clientIdFilter` — usado por:
 *   - /admin/messages/page.tsx → sin filter (cross-cliente)
 *   - /admin/clients/[id] tab Mensajes → con filter (single cliente)
 *
 * - Polling 15s
 * - Filter unread + cliente Select
 * - Click row → onSelectThread callback (parent maneja Sheet o nav)
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
import { useClients } from "@/hooks/useClients";

import { listAdminThreads } from "@/lib/admin-messages/api";
import type { ThreadSummary } from "@/lib/admin-messages/schemas";

interface AdminInboxListProps {
  /** Si presente, filtra por client_id (uso en MensajesTab). */
  clientIdFilter?: string;
  onSelectThread: (threadId: string) => void;
  pollingIntervalMs?: number;
}

export function AdminInboxList({
  clientIdFilter,
  onSelectThread,
  pollingIntervalMs = 15_000,
}: AdminInboxListProps) {
  const [threads, setThreads] = useState<ThreadSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<string | "">(
    clientIdFilter ?? "",
  );
  const { data: clients } = useClients();

  const effectiveClientFilter = clientIdFilter ?? (selectedClientId || null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function fetchThreads() {
      try {
        const data = await listAdminThreads({
          client_id: effectiveClientFilter,
          only_unread: onlyUnread,
        });
        if (!cancelled) {
          setThreads(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error cargando inbox");
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
  }, [effectiveClientFilter, onlyUnread, pollingIntervalMs]);

  const clientLookup = useMemo(() => {
    const m = new Map<string, string>();
    if (clients) for (const c of clients) m.set(c.id, c.nombre);
    return m;
  }, [clients]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {!clientIdFilter && (
          <select
            value={selectedClientId}
            onChange={(e) => setSelectedClientId(e.target.value)}
            className="rounded-md border border-fulkro-ink-300 px-2 py-1 text-sm"
            aria-label="Filtrar por cliente"
          >
            <option value="">Todos los clientes</option>
            {clients?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        )}
        <Button
          type="button"
          size="sm"
          variant={onlyUnread ? "primary" : "outline"}
          onClick={() => setOnlyUnread((v) => !v)}
          aria-pressed={onlyUnread}
        >
          {onlyUnread ? "✓ No leídos" : "Solo no leídos"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {threads === null ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : threads.length === 0 ? (
        <div className="rounded-md border border-fulkro-ink-200 bg-white p-6 text-center text-base font-medium text-[color:var(--fulkro-muted)]">
          No hay mensajes que mostrar.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              {!clientIdFilter && <TableHead>Cliente</TableHead>}
              <TableHead>Resumen</TableHead>
              <TableHead className="w-32">Último</TableHead>
              <TableHead className="w-24 text-center">Mensajes</TableHead>
              <TableHead className="w-24 text-center">No leídos</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {threads.map((t) => {
              const date = new Date(t.last_message_at);
              return (
                <TableRow
                  key={t.thread_id}
                  className="cursor-pointer hover:bg-fulkro-ink-50"
                  onClick={() => onSelectThread(t.thread_id)}
                  role="button"
                >
                  {!clientIdFilter && (
                    <TableCell className="font-medium">
                      {clientLookup.get(t.client_id) ?? t.client_id.slice(0, 8)}
                    </TableCell>
                  )}
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <span className="line-clamp-2 text-sm">
                        {t.last_message_excerpt}
                      </span>
                      <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                        Último de:{" "}
                        {t.last_message_from_role === "client"
                          ? "Cliente"
                          : "Marcos"}
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
                    {t.unread_for_admin > 0 ? (
                      <Badge variant="default">{t.unread_for_admin}</Badge>
                    ) : (
                      <span className="text-xs text-fulkro-ink-600">—</span>
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
