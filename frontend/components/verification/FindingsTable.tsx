"use client";

import { ChevronLeft, ChevronRight, Filter, Loader2, Search } from "lucide-react";
import * as React from "react";

import { FindingDetail } from "@/components/verification/FindingDetail";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { Input } from "@/components/ui/input";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useFindings, useVerificationRuns } from "@/hooks/useVerification";
import type {
  FindingStatus,
  FindingSummary,
  Severity,
  ZfpClassification,
} from "@/lib/verification-types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-fulkro-danger text-white",
  high: "bg-fulkro-danger-500 text-white",
  medium: "bg-fulkro-warning text-white",
  low: "bg-fulkro-info text-white",
  info: "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
};

const STATUS_STYLES: Record<FindingStatus, string> = {
  open: "bg-fulkro-danger/10 text-fulkro-danger",
  needs_review: "bg-fulkro-warning/10 text-fulkro-warning",
  remediated: "bg-fulkro-success/10 text-fulkro-success",
  accepted_risk: "bg-fulkro-info/10 text-fulkro-info",
  false_positive: "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
};

const CLASSIFICATION_LABEL: Record<ZfpClassification, string> = {
  confirmed: "confirmado",
  probable: "probable",
  needs_review: "revisar",
  rejected: "rechazado",
};

export function FindingsTable({ projectId }: { projectId: string }) {
  const runs = useVerificationRuns(projectId);
  const runsList = React.useMemo(
    () => runs.data?.runs ?? [],
    [runs.data?.runs],
  );
  const lastCompletedRun = React.useMemo(
    () => runsList.find((r) => r.status === "completed"),
    [runsList],
  );

  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);
  const effectiveRunId = selectedRunId ?? lastCompletedRun?.id ?? null;

  const [severity, setSeverity] = React.useState<string>("");
  const [status, setStatus] = React.useState<string>("");
  const [classification, setClassification] = React.useState<string>("");
  const [ensMeasure, setEnsMeasure] = React.useState<string>("");
  const [search, setSearch] = React.useState("");
  const [page, setPage] = React.useState(0);
  const [selected, setSelected] = React.useState<FindingSummary | null>(null);

  const findingsQ = useFindings(projectId, effectiveRunId, {
    severity: severity || undefined,
    status: status || undefined,
    classification: classification || undefined,
    ens_measure: ensMeasure || undefined,
  });

  const allFindings = React.useMemo(
    () => findingsQ.data?.findings ?? [],
    [findingsQ.data?.findings],
  );
  const filtered = React.useMemo(() => {
    if (!search.trim()) return allFindings;
    const q = search.toLowerCase();
    return allFindings.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.affected_host.toLowerCase().includes(q) ||
        (f.cve_id?.toLowerCase().includes(q) ?? false) ||
        (f.ens_primary_measure?.toLowerCase().includes(q) ?? false),
    );
  }, [allFindings, search]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPageFindings = filtered.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE,
  );

  React.useEffect(() => {
    setPage(0);
  }, [severity, status, classification, ensMeasure, search, effectiveRunId]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <CardTitle>
            Hallazgos{" "}
            <TooltipENS term="zero_false_positive" />
          </CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            {runsList.length > 0 && (
              <select
                value={effectiveRunId ?? ""}
                onChange={(e) => setSelectedRunId(e.target.value || null)}
                aria-label="Seleccionar run"
                className="rounded border border-[color:var(--fulkro-surface-glass-border)] bg-white px-2 py-1 text-xs font-mono"
              >
                {runsList.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id.slice(0, 8)}… · {r.category} · {r.status}
                  </option>
                ))}
              </select>
            )}
            <div className="relative">
              <Search
                size={12}
                className="absolute left-2 top-1/2 -translate-y-1/2 text-fulkro-ink-500"
                aria-hidden
              />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="título · host · CVE · medida"
                aria-label="Buscar hallazgos"
                className="h-8 pl-7 text-xs"
              />
            </div>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              aria-label="Filtrar por severidad"
              className="h-8 rounded border border-[color:var(--fulkro-surface-glass-border)] bg-white px-2 text-xs"
            >
              <option value="">Severidad (todas)</option>
              <option value="critical">Crítico</option>
              <option value="high">Alto</option>
              <option value="medium">Medio</option>
              <option value="low">Bajo</option>
              <option value="info">Info</option>
            </select>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              aria-label="Filtrar por estado"
              className="h-8 rounded border border-[color:var(--fulkro-surface-glass-border)] bg-white px-2 text-xs"
            >
              <option value="">Estado (todos)</option>
              <option value="open">Abierto</option>
              <option value="needs_review">Revisar</option>
              <option value="remediated">Remediado</option>
              <option value="accepted_risk">Riesgo aceptado</option>
              <option value="false_positive">Falso positivo</option>
            </select>
            <select
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
              aria-label="Filtrar por clasificación ZFP"
              className="h-8 rounded border border-[color:var(--fulkro-surface-glass-border)] bg-white px-2 text-xs"
            >
              <option value="">ZFP (todas)</option>
              <option value="confirmed">Confirmado</option>
              <option value="probable">Probable</option>
              <option value="needs_review">Revisar</option>
            </select>
            <Input
              value={ensMeasure}
              onChange={(e) => setEnsMeasure(e.target.value)}
              placeholder="op.exp.5"
              aria-label="Filtrar por medida ENS"
              className="h-8 w-24 text-xs font-mono"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        {!effectiveRunId && (
          <div className="p-6 text-base font-medium text-[color:var(--fulkro-muted)]">
            No hay runs completados todavía. Lanza una verificación para empezar.
          </div>
        )}
        {findingsQ.isLoading && effectiveRunId && (
          <div className="flex h-32 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
            <Loader2 size={14} className="animate-spin" /> cargando hallazgos…
          </div>
        )}
        {findingsQ.error && (
          <div className="p-6 text-sm text-fulkro-danger">
            Error: {(findingsQ.error as Error).message}
          </div>
        )}
        {findingsQ.data && currentPageFindings.length === 0 && (
          <div className="p-6 text-base font-medium text-[color:var(--fulkro-muted)]">
            No hay hallazgos con los filtros seleccionados.
          </div>
        )}
        {currentPageFindings.length > 0 && (
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b border-fulkro-ink-300/40 bg-fulkro-ink-100/50 text-left text-[11px] uppercase tracking-wider text-fulkro-ink-500">
                <th className="px-3 py-2">
                  Severidad <TooltipENS term="CVSS" />
                </th>
                <th className="px-3 py-2">Título</th>
                <th className="px-3 py-2">Host</th>
                <th className="px-3 py-2">
                  <InfoTag term="CVE" display="CVE" />
                </th>
                <th className="px-3 py-2">
                  Medida <InfoTag term="ENS" display="ENS" />
                </th>
                <th className="px-3 py-2">Confianza</th>
                <th className="px-3 py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {currentPageFindings.map((f) => (
                <tr
                  key={f.id}
                  onClick={() => setSelected(f)}
                  className="cursor-pointer border-b border-fulkro-ink-300/30 transition-colors hover:bg-[color:var(--fulkro-surface-glass)]"
                >
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "inline-block rounded px-2 py-0.5 text-[11px] font-semibold",
                        SEVERITY_STYLES[f.severity],
                      )}
                    >
                      {f.severity}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <p className="font-medium text-fulkro-primary-700">{f.title}</p>
                    <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                      ZFP: {CLASSIFICATION_LABEL[f.zfp_gate5_classification]} (
                      {f.confidence_score.toFixed(2)})
                    </p>
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px]">
                    {f.affected_host}
                    {f.affected_port ? `:${f.affected_port}` : ""}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px]">
                    {f.cve_id ?? "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px]">
                    {f.ens_primary_measure ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-fulkro-ink-300/40">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            f.confidence_score >= 0.9
                              ? "bg-fulkro-success"
                              : f.confidence_score >= 0.7
                                ? "bg-fulkro-warning"
                                : "bg-fulkro-danger",
                          )}
                          style={{ width: `${f.confidence_score * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                        {(f.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[11px] font-semibold",
                        STATUS_STYLES[f.status],
                      )}
                    >
                      {f.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {filtered.length > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-fulkro-ink-300/40 px-4 py-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
            <span>
              Mostrando {page * PAGE_SIZE + 1}–
              {Math.min((page + 1) * PAGE_SIZE, filtered.length)} de{" "}
              {filtered.length}
            </span>
            <div className="flex gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                aria-label="Página anterior"
              >
                <ChevronLeft size={12} />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setPage((p) => Math.min(pageCount - 1, p + 1))
                }
                disabled={page >= pageCount - 1}
                aria-label="Página siguiente"
              >
                <ChevronRight size={12} />
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      {selected && (
        <FindingDetail
          projectId={projectId}
          finding={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </Card>
  );
}
