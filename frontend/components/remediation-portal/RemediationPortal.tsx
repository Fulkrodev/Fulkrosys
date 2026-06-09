"use client";

import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  RefreshCcw,
  Shield,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { RemediationGuideModal } from "@/components/remediation-portal/RemediationGuideModal";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getRemediationData,
  markRemediationFixed,
} from "@/lib/api/public-portals";
import type {
  RemediationData,
  RemediationFindingCard,
  RemediationRetestResult,
  Severity,
} from "@/lib/public-portals-types";
import { cn, formatDate } from "@/lib/utils";

const SEVERITY_STYLES: Record<
  Severity,
  { label: string; emoji: string; cardBorder: string; pill: string; bucket: string }
> = {
  critical: {
    label: "Crítico",
    emoji: "🔴",
    cardBorder: "border-l-4 border-l-fulkro-danger",
    pill: "bg-fulkro-danger text-white",
    bucket: "bg-fulkro-danger/10 border-fulkro-danger/40",
  },
  high: {
    label: "Alto",
    emoji: "🟠",
    cardBorder: "border-l-4 border-l-fulkro-danger/70",
    pill: "bg-fulkro-danger/70 text-white",
    bucket: "bg-fulkro-danger/5 border-fulkro-danger/30",
  },
  medium: {
    label: "Medio",
    emoji: "🟡",
    cardBorder: "border-l-4 border-l-fulkro-warning",
    pill: "bg-fulkro-warning text-white",
    bucket: "bg-fulkro-warning/10 border-fulkro-warning/40",
  },
  low: {
    label: "Bajo",
    emoji: "🔵",
    cardBorder: "border-l-4 border-l-fulkro-info",
    pill: "bg-fulkro-info text-white",
    bucket: "bg-fulkro-info/10 border-fulkro-info/40",
  },
  info: {
    label: "Info",
    emoji: "⚪",
    cardBorder: "border-l-4 border-l-fulkro-ink-300",
    pill: "bg-fulkro-ink-100 text-fulkro-ink-600",
    bucket: "bg-fulkro-ink-100 border-fulkro-ink-300/60",
  },
};

export function RemediationPortal({ token }: { token: string }) {
  const [data, setData] = React.useState<RemediationData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [selected, setSelected] =
    React.useState<RemediationFindingCard | null>(null);
  const [resolvedExpanded, setResolvedExpanded] = React.useState(false);
  const [pendingAck, setPendingAck] =
    React.useState<{ finding_id: string; result: RemediationRetestResult } | null>(null);
  const [fixingId, setFixingId] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    try {
      const d = await getRemediationData(token);
      setData(d);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  async function quickFixed(f: RemediationFindingCard) {
    setFixingId(f.finding_id);
    try {
      const result = await markRemediationFixed(token, f.finding_id);
      setPendingAck({ finding_id: f.finding_id, result });
      await refresh();
    } catch (e) {
      toast.error("No se pudo verificar la corrección", {
        description: (e as Error).message,
      });
    } finally {
      setFixingId(null);
    }
  }

  function onFixedFromModal(result: RemediationRetestResult) {
    setPendingAck({ finding_id: result.finding_id, result });
    setSelected(null);
    refresh();
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex h-40 items-center justify-center gap-2 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" />
          Cargando estado de seguridad…
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          No se pudo cargar el portal. Es posible que el enlace haya caducado
          o haya sido revocado. Contacta con tu consultor ENS.
          <p className="mt-2 text-xs text-fulkro-ink-500">
            Detalle técnico: {error}
          </p>
        </CardContent>
      </Card>
    );
  }

  const severityEntries = (
    ["critical", "high", "medium", "low"] as const
  ).map((sev) => ({
    sev,
    style: SEVERITY_STYLES[sev],
    pending: data.severity_buckets[sev]?.pending ?? 0,
    total: data.severity_buckets[sev]?.total ?? 0,
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield size={18} className="text-fulkro-primary-700" />
                Estado de seguridad — {data.cliente.razon_social}
              </CardTitle>
              {data.scope.scan_date && (
                <p className="mt-1 text-sm text-fulkro-ink-500">
                  Último análisis: {formatDate(data.scope.scan_date)}
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              className="gap-1"
              aria-label="Refrescar estado"
            >
              <RefreshCcw size={12} /> Refrescar
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-2 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
            <span className="text-sm font-semibold text-fulkro-primary-700">
              {data.progress.resolved} de {data.progress.total} hallazgos
              resueltos
            </span>
            <span className="text-xs text-fulkro-ink-500">
              {data.progress.pct}% completado
            </span>
          </p>
          <div
            className="h-3 w-full overflow-hidden rounded-full bg-fulkro-ink-100"
            role="progressbar"
            aria-label="Progreso de remediación"
            aria-valuenow={Math.round(data.progress.pct)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-fulkro-danger via-fulkro-warning to-fulkro-success transition-all duration-500"
              style={{ width: `${data.progress.pct}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Severity buckets */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {severityEntries.map(({ sev, style, pending, total }) => (
          <Card
            key={sev}
            className={cn("border", style.bucket)}
            aria-label={`Severidad ${style.label}: ${pending} pendientes de ${total}`}
          >
            <CardContent className="flex flex-col gap-1 p-3">
              <div className="flex items-center gap-2">
                <span aria-hidden className="text-base">
                  {style.emoji}
                </span>
                <span className="text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
                  {style.label}
                </span>
              </div>
              <p className="text-xl font-semibold text-fulkro-primary-700">
                {pending}{" "}
                <span className="text-sm font-normal text-fulkro-ink-500">
                  de {total} pendiente{pending === 1 ? "" : "s"}
                </span>
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Success message tras retest exitoso */}
      {pendingAck?.result?.retest_result === "fixed" && (
        <Card className="border-fulkro-success/40 bg-fulkro-success/5">
          <CardContent className="flex items-start gap-2 p-4">
            <CheckCircle2 size={18} className="mt-0.5 text-fulkro-success" />
            <div>
              <p className="font-semibold text-fulkro-primary-700">
                Hallazgo resuelto y verificado
              </p>
              <p className="mt-1 text-sm text-fulkro-ink-500">
                Verificado el{" "}
                {pendingAck.result.verified_at
                  ? formatDate(pendingAck.result.verified_at)
                  : "ahora"}
                . Ya no aparece como pendiente.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPendingAck(null)}
              className="ml-auto"
              aria-label="Cerrar confirmación"
            >
              OK
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Still-present message */}
      {pendingAck?.result?.retest_result === "still_present" && (
        <Card className="border-fulkro-warning/40 bg-fulkro-warning/5">
          <CardContent className="flex items-start gap-2 p-4">
            <AlertCircle size={18} className="mt-0.5 text-fulkro-warning" />
            <div>
              <p className="font-semibold text-fulkro-primary-700">
                El hallazgo sigue presente
              </p>
              <p className="mt-1 text-sm text-fulkro-ink-700">
                {pendingAck.result.retest_detail ??
                  "La comprobación automática todavía detecta el problema."}
              </p>
              <p className="mt-2 text-xs text-fulkro-ink-500">
                ¿Necesitas ayuda? Escribe a tu consultor ENS para revisar los
                pasos aplicados.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPendingAck(null)}
              className="ml-auto"
            >
              OK
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Pending findings */}
      <section aria-labelledby="pendientes-h">
        <h2
          id="pendientes-h"
          className="mb-2 text-sm font-semibold uppercase tracking-wider text-fulkro-ink-500"
        >
          Pendientes ({data.pending_findings.length})
        </h2>
        {data.pending_findings.length === 0 ? (
          <Card>
            <CardContent className="flex items-center gap-2 p-4 text-sm text-fulkro-success">
              <CheckCircle2 size={16} /> No hay hallazgos pendientes. Gran
              trabajo.
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            {data.pending_findings.map((f) => {
              const style = SEVERITY_STYLES[f.severity];
              return (
                <Card
                  key={f.finding_id}
                  className={cn("overflow-hidden", style.cardBorder)}
                >
                  <CardContent className="flex flex-col gap-2 p-4">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={cn(
                              "rounded px-2 py-0.5 text-[11px] font-semibold uppercase",
                              style.pill,
                            )}
                          >
                            {style.label}
                          </span>
                          <h3 className="font-semibold text-fulkro-primary-700">
                            {f.title}
                          </h3>
                        </div>
                        <p className="mt-1 font-mono text-[11px] text-fulkro-ink-500">
                          {f.host_port}
                        </p>
                      </div>
                    </div>
                    <p className="text-sm text-fulkro-ink-700">
                      {f.summary_non_technical}
                    </p>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-fulkro-ink-500">
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> {f.time_estimate}
                      </span>
                      <span>
                        Reinicio:{" "}
                        <span className="font-semibold">
                          {f.requires_restart ? "sí" : "no"}
                        </span>
                      </span>
                      {f.requires_maintenance_window && (
                        <span className="rounded bg-fulkro-warning/10 px-2 py-0.5 text-fulkro-warning">
                          Ventana recomendada
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelected(f)}
                        className="w-full sm:w-auto"
                      >
                        Ver guía de solución
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => quickFixed(f)}
                        disabled={fixingId === f.finding_id}
                        className="w-full gap-1 sm:w-auto"
                      >
                        {fixingId === f.finding_id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <CheckCircle2 size={14} />
                        )}
                        {fixingId === f.finding_id
                          ? "Verificando…"
                          : "Ya lo he arreglado"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {/* Resolved findings */}
      {data.resolved_findings.length > 0 && (
        <section>
          <button
            type="button"
            onClick={() => setResolvedExpanded((v) => !v)}
            aria-expanded={resolvedExpanded}
            className="mb-2 flex w-full items-center justify-between rounded-md border border-fulkro-ink-300/60 bg-white px-3 py-2 text-sm font-semibold text-fulkro-primary-700 hover:bg-fulkro-ink-100"
          >
            <span>
              Resueltos ({data.resolved_findings.length})
            </span>
            {resolvedExpanded ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronRight size={14} />
            )}
          </button>
          {resolvedExpanded && (
            <ul className="flex flex-col gap-1 text-sm">
              {data.resolved_findings.map((r) => {
                const style = SEVERITY_STYLES[r.severity];
                return (
                  <li
                    key={r.finding_id}
                    className="flex flex-col gap-1 rounded border border-fulkro-ink-300/40 bg-white px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <span className="flex items-center gap-2">
                      <CheckCircle2 size={14} className="text-fulkro-success" />
                      <span className="font-medium text-fulkro-primary-700">
                        {r.title}
                      </span>
                      <span
                        className={cn(
                          "rounded px-1.5 text-[10px] font-semibold uppercase",
                          style.pill,
                        )}
                      >
                        {style.label}
                      </span>
                    </span>
                    {r.remediated_at && (
                      <span className="text-xs text-fulkro-ink-500">
                        resuelto {formatDate(r.remediated_at)}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {selected && (
        <RemediationGuideModal
          token={token}
          finding={selected}
          onClose={() => setSelected(null)}
          onFixed={onFixedFromModal}
        />
      )}
    </div>
  );
}
