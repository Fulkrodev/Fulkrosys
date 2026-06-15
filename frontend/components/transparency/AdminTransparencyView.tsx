"use client";

/**
 * AdminTransparencyView · sub-atom 1.E.1.B.2.
 *
 * Admin full view AI Act art.50 transparency log per proyecto · includes
 * technical fields (llm_provider · llm_model · metadata) para auditor ENAC
 * forensic review. R23 sostener (project-scoped).
 *
 * Endpoint: /api/v1/admin/projects/{id}/transparency/log
 */
import { useEffect, useState } from "react";
import { Loader2, ScrollText } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type AdminTransparencyEvent,
  type AdminTransparencyLogResponse,
  getAdminProjectTransparencyLog,
} from "@/lib/api/transparency-admin";
import { EVENT_TYPE_LABEL } from "@/lib/api/transparency-client";

type DaysWindow = 30 | 90 | 180 | 365;

const DAYS_OPTIONS: DaysWindow[] = [30, 90, 180, 365];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

interface Props {
  projectId: string;
}

export function AdminTransparencyView({ projectId }: Props) {
  const [days, setDays] = useState<DaysWindow>(180);
  const [data, setData] = useState<AdminTransparencyLogResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAdminProjectTransparencyLog(projectId, days)
      .then((resp) => {
        if (!cancelled) setData(resp);
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof Error
            ? err.message
            : "Error cargando transparency log";
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, days]);

  const items: AdminTransparencyEvent[] = data?.items ?? [];

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
            Transparencia IA · AI Act art.50
          </h1>
          <p className="text-sm font-medium text-[color:var(--fulkro-body)]">
            Audit trail completo decisiones IA externalizadas por proyecto ·
            auditor ENAC forensic ready · retention 6 años per AI Act.
          </p>
        </div>
        <div
          className="flex gap-2"
          data-testid="transparency-admin-days-filter"
        >
          {DAYS_OPTIONS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDays(d)}
              className={`rounded-md px-3 py-1.5 text-sm font-bold ${
                d === days
                  ? "bg-[color:var(--fulkro-accent)] text-white"
                  : "bg-fulkro-surface-glass-strong text-[color:var(--fulkro-body)] hover:bg-fulkro-surface-glass"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ScrollText className="h-4 w-4" />
            Eventos registrados · últimos {data?.days ?? days} días
            {data ? ` · ${data.total} total` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="grid place-items-center py-10 text-[color:var(--fulkro-muted)]">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}

          {!loading && error && (
            <p
              className="text-sm text-amber-700"
              data-testid="transparency-admin-error"
            >
              {error}
            </p>
          )}

          {!loading && !error && items.length === 0 && (
            <p
              className="text-sm text-[color:var(--fulkro-muted)]"
              data-testid="transparency-admin-empty"
            >
              Sin eventos registrados en este periodo.
            </p>
          )}

          {!loading && !error && items.length > 0 && (
            <div
              className="overflow-x-auto"
              data-testid="transparency-admin-table"
            >
              <table className="min-w-full divide-y divide-fulkro-ink-100 text-sm">
                <thead className="bg-fulkro-ink-50 text-left text-xs font-medium uppercase tracking-wide text-fulkro-ink-500">
                  <tr>
                    <th className="px-3 py-2">Fecha</th>
                    <th className="px-3 py-2">Tipo</th>
                    <th className="px-3 py-2">Agente</th>
                    <th className="px-3 py-2">Proveedor / Modelo</th>
                    <th className="px-3 py-2">Artefacto</th>
                    <th className="px-3 py-2">Propósito</th>
                    <th className="px-3 py-2">Retención hasta</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-fulkro-ink-100 bg-white">
                  {items.map((it) => (
                    <tr
                      key={it.id}
                      data-testid={`transparency-admin-row-${it.id}`}
                    >
                      <td className="whitespace-nowrap px-3 py-2 text-fulkro-ink-700">
                        {formatDate(it.created_at)}
                      </td>
                      <td className="px-3 py-2 text-fulkro-ink-900">
                        {EVENT_TYPE_LABEL[it.event_type] ?? it.event_type}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-fulkro-ink-600">
                        {it.agent_name}
                      </td>
                      <td className="px-3 py-2 text-fulkro-ink-600">
                        <code className="rounded bg-fulkro-ink-100 px-1 text-xs">
                          {it.llm_provider} / {it.llm_model}
                        </code>
                      </td>
                      <td className="px-3 py-2 text-fulkro-ink-600">
                        {it.artifact_type ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-fulkro-ink-700">
                        {it.purpose}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-fulkro-ink-600">
                        {it.retention_until}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
