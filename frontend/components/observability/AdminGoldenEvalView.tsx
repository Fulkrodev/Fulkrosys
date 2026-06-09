"use client";

/**
 * AdminGoldenEvalView · sub-atom 1.E.1.B.3.E.
 *
 * Admin UI golden eval runs · trigger + historical runs · multi-agent
 * ready (datasets dropdown). Skeleton phase B.3.D Path C-light:
 * entries skipped state empíricamente visible · "capability_pending_build"
 * badge informativo.
 *
 * Pattern reuse AdminTransparencyView (1.E.1.B.2 commit fd903fe).
 */
import { useMemo, useState } from "react";
import { Loader2, PlayCircle, ScrollText } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  SEVERITY_LABEL,
  STATUS_LABEL,
  type GoldenEvalRunDetail,
  type GoldenEvalSeverity,
  type GoldenEvalRunStatus,
} from "@/lib/api/golden-eval-admin";
import { useGoldenEvalRuns } from "@/hooks/useGoldenEvalRuns";

type DaysWindow = 7 | 30 | 90 | 180;

const DAYS_OPTIONS: DaysWindow[] = [7, 30, 90, 180];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
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

function severityBadgeClass(severity: GoldenEvalSeverity | null): string {
  switch (severity) {
    case "ok":
      return "bg-emerald-100 text-emerald-800";
    case "warn":
      return "bg-amber-100 text-amber-800";
    case "alert":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

function statusBadgeClass(status: GoldenEvalRunStatus): string {
  switch (status) {
    case "completed":
      return "bg-slate-100 text-slate-700";
    case "running":
      return "bg-indigo-100 text-indigo-800";
    case "queued":
      return "bg-slate-50 text-slate-600";
    case "failed":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

function CapabilityPendingBanner({
  runs,
}: {
  runs: GoldenEvalRunDetail[];
}) {
  // Detectar si último run completed tiene entries_evaluated=0 mientras
  // entries_in_dataset > 0 · señal capability pending build (B.3.D)
  const latestCompleted = runs.find((r) => r.status === "completed");
  if (!latestCompleted) return null;
  const skipped =
    latestCompleted.entries_in_dataset > 0 &&
    latestCompleted.entries_evaluated === 0;
  if (!skipped) return null;
  return (
    <div
      className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
      data-testid="capability-pending-banner"
    >
      <strong>Capability pending build · skeleton phase.</strong>
      <span className="ml-1">
        Todas las entries skipped (10/10) · DeliverableTextAuditor capability
        construible en{" "}
        <code className="rounded bg-amber-100 px-1">
          Future-1.E.1.dossier-pack-10docs
        </code>
        . Path C-light sostained (3-point commitment).
      </span>
    </div>
  );
}

export function AdminGoldenEvalView() {
  const {
    loading,
    error,
    datasets,
    runs,
    totalRuns,
    daysWindow,
    selectedAgent,
    setSelectedAgent,
    setDaysWindow,
    triggering,
    triggerError,
    trigger,
  } = useGoldenEvalRuns(30);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const detail = useMemo(
    () => runs.find((r) => r.id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
            Golden Eval · Regression Harness
          </h1>
          <p className="text-sm font-medium text-[color:var(--fulkro-body)]">
            Dispara evaluaciones golden contra datasets curados · regresión
            detection post-prompt-change · post-model-bump.
          </p>
        </div>
        <div
          className="flex gap-2"
          data-testid="golden-eval-days-filter"
        >
          {DAYS_OPTIONS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDaysWindow(d)}
              className={`rounded-md px-3 py-1.5 text-sm font-bold ${
                d === daysWindow
                  ? "bg-[color:var(--fulkro-accent)] text-white"
                  : "bg-fulkro-surface-glass-strong text-[color:var(--fulkro-body)] hover:bg-fulkro-surface-glass"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </header>

      <CapabilityPendingBanner runs={runs} />

      {/* Datasets · trigger */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <PlayCircle className="h-4 w-4" />
            Datasets disponibles ({datasets.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {datasets.length === 0 && !loading && (
            <p
              className="text-sm text-[color:var(--fulkro-muted)]"
              data-testid="datasets-empty"
            >
              Sin datasets curados todavía. Añadir en{" "}
              <code>docs/catalogs/golden_datasets/</code>.
            </p>
          )}
          {datasets.length > 0 && (
            <div
              className="flex flex-col gap-2"
              data-testid="datasets-list"
            >
              {datasets.map((ds) => (
                <div
                  key={`${ds.agent_name}:${ds.version}`}
                  className="flex items-center justify-between rounded-md border border-slate-100 p-3"
                  data-testid={`dataset-${ds.agent_name}`}
                >
                  <div>
                    <code className="text-sm font-semibold text-slate-900">
                      {ds.agent_name}
                    </code>
                    <span className="ml-2 text-xs text-slate-500">
                      {ds.version}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      void trigger({
                        agent_name: ds.agent_name,
                        version: ds.version,
                      })
                    }
                    disabled={triggering}
                    className="rounded-md bg-[color:var(--fulkro-accent)] px-3 py-1.5 text-sm font-bold text-white disabled:opacity-50"
                    data-testid={`trigger-${ds.agent_name}`}
                  >
                    {triggering ? "Ejecutando…" : "Ejecutar evaluación"}
                  </button>
                </div>
              ))}
            </div>
          )}
          {triggerError && (
            <p
              className="mt-3 text-sm text-amber-700"
              data-testid="trigger-error"
            >
              {triggerError}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Historical runs */}
      <Card>
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <ScrollText className="h-4 w-4" />
            Runs históricos · {daysWindow}d{" · "}
            {totalRuns} total
          </CardTitle>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setSelectedAgent(null)}
              className={`rounded-md px-2 py-1 text-xs ${
                selectedAgent === null
                  ? "bg-slate-700 text-white"
                  : "bg-slate-100 text-slate-700"
              }`}
            >
              Todos
            </button>
            {datasets.map((ds) => (
              <button
                key={`filter-${ds.agent_name}`}
                type="button"
                onClick={() => setSelectedAgent(ds.agent_name)}
                className={`rounded-md px-2 py-1 text-xs ${
                  selectedAgent === ds.agent_name
                    ? "bg-slate-700 text-white"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                {ds.agent_name}
              </button>
            ))}
          </div>
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
              data-testid="runs-error"
            >
              {error}
            </p>
          )}
          {!loading && !error && runs.length === 0 && (
            <p
              className="text-sm text-[color:var(--fulkro-muted)]"
              data-testid="runs-empty"
            >
              Sin runs registrados en este periodo.
            </p>
          )}
          {!loading && !error && runs.length > 0 && (
            <div
              className="overflow-x-auto"
              data-testid="runs-table"
            >
              <table className="min-w-full divide-y divide-slate-100 text-sm">
                <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Fecha</th>
                    <th className="px-3 py-2">Agent</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2">Score</th>
                    <th className="px-3 py-2">Eval/Total</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {runs.map((run) => (
                    <tr
                      key={run.id}
                      data-testid={`run-row-${run.id}`}
                    >
                      <td className="whitespace-nowrap px-3 py-2 text-slate-700">
                        {formatDate(run.triggered_at)}
                      </td>
                      <td className="px-3 py-2 text-slate-900">
                        <code className="text-xs">{run.agent_name}</code>
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(
                            run.status,
                          )}`}
                        >
                          {STATUS_LABEL[run.status]}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {run.severity ? (
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${severityBadgeClass(
                              run.severity,
                            )}`}
                          >
                            {SEVERITY_LABEL[run.severity]}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        {run.regression_score !== null
                          ? `${(run.regression_score * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        {run.entries_evaluated}/{run.entries_in_dataset}
                      </td>
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => setSelectedRunId(run.id)}
                          className="text-xs text-[color:var(--fulkro-accent)] hover:underline"
                          data-testid={`run-detail-${run.id}`}
                        >
                          Detalle
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Run detail drawer (inline panel) */}
      {detail && (
        <Card data-testid="run-detail-panel">
          <CardHeader>
            <CardTitle className="text-base">
              Detalle · {detail.agent_name} · {formatDate(detail.triggered_at)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-xs uppercase text-slate-500">Status</dt>
                <dd className="font-medium text-slate-900">
                  {STATUS_LABEL[detail.status]}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">Severity</dt>
                <dd className="font-medium text-slate-900">
                  {detail.severity ? SEVERITY_LABEL[detail.severity] : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">
                  Regression score
                </dt>
                <dd className="font-medium text-slate-900">
                  {detail.regression_score !== null
                    ? `${(detail.regression_score * 100).toFixed(1)}%`
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">
                  Entries (eval/total)
                </dt>
                <dd className="font-medium text-slate-900">
                  {detail.entries_evaluated}/{detail.entries_in_dataset}
                </dd>
              </div>
            </dl>
            {detail.failed_entry_ids && detail.failed_entry_ids.length > 0 && (
              <div className="mt-4">
                <p className="text-xs uppercase text-slate-500">
                  Entries fallidos
                </p>
                <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                  {detail.failed_entry_ids.map((eid) => (
                    <li key={eid}>
                      <code>{eid}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {detail.error_message && (
              <p className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-800">
                {detail.error_message}
              </p>
            )}
            <button
              type="button"
              onClick={() => setSelectedRunId(null)}
              className="mt-4 text-xs text-[color:var(--fulkro-accent)] hover:underline"
            >
              Cerrar
            </button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
