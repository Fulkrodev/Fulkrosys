"use client";

/**
 * /admin/timesheet · MB-7.bis atom 7.bis.5 Q6.C.
 *
 * Marcos timesheet · summary tile + entries table + manual entry quick-add.
 * Source: GET/POST /api/v1/admin/timesheet/*.
 */
import { Clock, Loader2, Plus, Receipt } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";


interface TimesheetEntry {
  id: string;
  client_id: string;
  retainer_id: string | null;
  activity_id: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_minutes: number | null;
  source: string;
  manual_override: boolean;
  endpoint_path: string | null;
  notes: string | null;
}


interface TopClient {
  client_id: string;
  client_name: string;
  total_minutes: number;
}


interface Summary {
  monthly_total_minutes: number;
  monthly_total_hours: number;
  top_clients: TopClient[];
}


function minutesToHm(minutes: number | null): string {
  if (minutes == null) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}


function formatTs(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


export default function TimesheetPage() {
  const [entries, setEntries] = useState<TimesheetEntry[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);

  const refetch = async () => {
    setLoading(true);
    try {
      const [entriesResp, summaryResp] = await Promise.all([
        api<{ items: TimesheetEntry[] }>("/api/v1/admin/timesheet/entries?limit=50"),
        api<Summary>("/api/v1/admin/timesheet/summary"),
      ]);
      setEntries(entriesResp.items);
      setSummary(summaryResp);
    } catch {
      setEntries([]);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refetch();
  }, []);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
            Mi timesheet
          </h1>
          <p className="text-base font-medium text-[color:var(--fulkro-body)]">
            Horas dedicadas a clientes este mes · auto-track endpoints + entradas manuales.
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={() => setShowAdd((v) => !v)}
        >
          <Plus className="h-4 w-4" /> Añadir manual
        </Button>
      </header>

      {summary && (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <CardContent className="p-5">
              <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                Total este mes
              </p>
              <div className="mt-2 flex items-center gap-3">
                <Clock className="h-7 w-7 text-[color:var(--fulkro-accent)]" />
                <p className="text-4xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
                  {summary.monthly_total_hours}h
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top 3 clientes (mes)</CardTitle>
            </CardHeader>
            <CardContent>
              {summary.top_clients.length === 0 ? (
                <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                  Sin actividad este mes.
                </p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {summary.top_clients.map((c) => (
                    <li
                      key={c.client_id}
                      className="flex items-center justify-between"
                    >
                      <span className="font-medium">{c.client_name}</span>
                      <span className="font-bold">
                        {minutesToHm(c.total_minutes)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </section>
      )}

      {showAdd && (
        <ManualEntryForm
          onCreated={() => {
            setShowAdd(false);
            void refetch();
          }}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" /> Entradas recientes
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="grid place-items-center py-8 text-[color:var(--fulkro-muted)]">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : entries.length === 0 ? (
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              Sin entradas registradas.
            </p>
          ) : (
            <table
              aria-label="Registros de horas (timesheet)"
              className="w-full text-sm"
              data-testid="timesheet-entries-table"
            >
              <thead className="text-left text-xs font-bold uppercase text-[color:var(--fulkro-subtitle)]">
                <tr>
                  <th className="pb-2">Inicio</th>
                  <th className="pb-2">Fin</th>
                  <th className="pb-2 text-right">Duración</th>
                  <th className="pb-2">Source</th>
                  <th className="pb-2">Notas</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} className="border-t border-fulkro-surface-glass-border">
                    <td className="py-2">{formatTs(e.started_at)}</td>
                    <td className="py-2">{formatTs(e.ended_at)}</td>
                    <td className="py-2 text-right font-bold">
                      {minutesToHm(e.duration_minutes)}
                    </td>
                    <td className="py-2 text-xs">
                      {e.source}
                      {e.manual_override && (
                        <span className="ml-1 rounded bg-amber-500/15 px-1 text-[10px] text-amber-700">
                          override
                        </span>
                      )}
                    </td>
                    <td className="py-2 text-xs text-[color:var(--fulkro-muted)]">
                      {e.notes ?? e.endpoint_path ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


function ManualEntryForm({ onCreated }: { onCreated: () => void }) {
  const [clientId, setClientId] = useState("");
  const [startedAt, setStartedAt] = useState(() =>
    new Date(Date.now() - 60 * 60 * 1000).toISOString().slice(0, 16),
  );
  const [duration, setDuration] = useState("30");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api("/api/v1/admin/timesheet/manual-entry", {
        method: "POST",
        json: {
          client_id: clientId,
          started_at: new Date(startedAt).toISOString(),
          duration_minutes: Number(duration),
          notes: notes || null,
        },
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error añadiendo entrada");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Nueva entrada manual</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-bold">Cliente ID (UUID)</span>
            <input
              type="text"
              required
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
              data-testid="timesheet-client-id"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-bold">Inicio</span>
            <input
              type="datetime-local"
              required
              value={startedAt}
              onChange={(e) => setStartedAt(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-bold">Duración (min)</span>
            <input
              type="number"
              min={1}
              max={1440}
              required
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm md:col-span-2">
            <span className="font-bold">Notas (opcional)</span>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
            />
          </label>
          {error && (
            <div className="md:col-span-2 rounded-md border border-rose-300/40 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-700">
              {error}
            </div>
          )}
          <div className="md:col-span-2 flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={submitting}
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Guardar entrada
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
