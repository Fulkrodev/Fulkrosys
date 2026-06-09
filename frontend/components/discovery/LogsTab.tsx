"use client";

import * as React from "react";
import { CheckCircle2, FileSearch, ScrollText, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import { useLoggingAssessment } from "@/hooks/useDiscovery";

export interface LogsTabProps {
  projectId: string;
}

function CoverageBar({ label, value }: { label: string; value: number | null }) {
  const pct = value ?? 0;
  const variant =
    pct >= 90 ? "success" : pct >= 70 ? "info" : pct >= 50 ? "warning" : "danger";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-fulkro-ink-700">{label}</span>
        <span className="font-mono">{value !== null ? `${pct}%` : "—"}</span>
      </div>
      <div className="h-2 overflow-hidden rounded bg-fulkro-canvas">
        <div
          className={cn(
            "h-full transition-all",
            variant === "success" && "bg-fulkro-success",
            variant === "info" && "bg-fulkro-info",
            variant === "warning" && "bg-fulkro-warning",
            variant === "danger" && "bg-destructive",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function LogsTab({ projectId }: LogsTabProps) {
  const { data, isLoading } = useLoggingAssessment(projectId);

  if (isLoading) {
    return <p className="text-sm text-fulkro-ink-500">Cargando evaluación logs…</p>;
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center gap-2 rounded border border-dashed border-fulkro-ink-200 py-10 text-fulkro-ink-500">
        <FileSearch className="size-8" />
        <p className="text-sm">Sin evaluación de logging</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <ScrollText size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">Logging y SIEM</h3>
          <TooltipENS term="siem" />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">Madurez {data.nivel_madurez_logging}</Badge>
          {data.cumple_op_exp_8 ? (
            <Badge variant="success">
              <CheckCircle2 className="mr-1 size-3" /> ENS OP.EXP.8 OK
            </Badge>
          ) : (
            <Badge variant="danger">
              <XCircle className="mr-1 size-3" /> ENS OP.EXP.8 gap
            </Badge>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">SIEM</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>SIEM activo</span>
              {data.tiene_siem === null ? (
                <Badge variant="secondary">—</Badge>
              ) : data.tiene_siem ? (
                <Badge variant="success">sí</Badge>
              ) : (
                <Badge variant="danger">no</Badge>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span>Producto</span>
              <span className="font-mono text-xs">{data.siem_producto ?? "—"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Casos de uso activos</span>
              <span className="font-mono">{data.casos_uso_activos ?? "—"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Alertas activas</span>
              {data.tiene_alertas_activas === null ? (
                <Badge variant="secondary">—</Badge>
              ) : data.tiene_alertas_activas ? (
                <Badge variant="success">sí</Badge>
              ) : (
                <Badge variant="warning">no</Badge>
              )}
            </div>
            <div className="text-xs text-fulkro-ink-500">
              Revisión: {data.alertas_revisadas_por ?? "—"}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm inline-flex items-center gap-1">
              Cobertura por capa <TooltipENS term="log_management" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <CoverageBar label="Servidores" value={data.cobertura.servidores} />
            <CoverageBar label="Red" value={data.cobertura.red} />
            <CoverageBar label="Aplicaciones" value={data.cobertura.aplicaciones} />
            <CoverageBar label="Endpoints" value={data.cobertura.endpoints} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Retención</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>Mínima</span>
              <span className="font-mono">
                {data.retencion_minima_dias !== null ? `${data.retencion_minima_dias}d` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Máxima</span>
              <span className="font-mono">
                {data.retencion_maxima_dias !== null ? `${data.retencion_maxima_dias}d` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Cumple ENS</span>
              {data.cumple_retencion_ens === null ? (
                <Badge variant="secondary">—</Badge>
              ) : data.cumple_retencion_ens ? (
                <Badge variant="success">sí</Badge>
              ) : (
                <Badge variant="danger">no</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Fuentes de log</CardTitle>
          </CardHeader>
          <CardContent>
            {data.fuentes_log.length === 0 ? (
              <p className="text-sm text-fulkro-ink-500">Ninguna fuente registrada</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {data.fuentes_log.map((f) => (
                  <Badge key={f} variant="outline">{f}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {data.gaps_op_exp_8.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-fulkro-warning">
              Gaps OP.EXP.8 ({data.gaps_op_exp_8.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {data.gaps_op_exp_8.map((g, i) => (
                <li key={i} className="text-fulkro-ink-700">· {g}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {data.observaciones ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Observaciones</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-fulkro-ink-700">{data.observaciones}</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
