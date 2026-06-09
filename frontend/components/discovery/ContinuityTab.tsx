"use client";

import * as React from "react";
import { Activity, AlertCircle, FileWarning, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import { useContinuityAssessment } from "@/hooks/useDiscovery";

export interface ContinuityTabProps {
  projectId: string;
}

function StatusBadge({ value, labelOk = "sí", labelKo = "no" }: { value: boolean | null; labelOk?: string; labelKo?: string }) {
  if (value === null) return <Badge variant="secondary">—</Badge>;
  return value ? (
    <Badge variant="success">{labelOk}</Badge>
  ) : (
    <Badge variant="danger">{labelKo}</Badge>
  );
}

export function ContinuityTab({ projectId }: ContinuityTabProps) {
  const { data, isLoading } = useContinuityAssessment(projectId);

  if (isLoading) {
    return <p className="text-sm text-fulkro-ink-500">Cargando evaluación…</p>;
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center gap-2 rounded border border-dashed border-fulkro-ink-200 py-10 text-fulkro-ink-500">
        <Activity className="size-8" />
        <p className="text-sm">Sin evaluación de continuidad · ejecuta scan o registra manualmente</p>
      </div>
    );
  }

  const formatDate = (s: string | null) => (s ? new Date(s).toLocaleDateString("es-ES") : "—");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Activity size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">Continuidad de negocio</h3>
          <TooltipENS term="BIA" />
        </div>
        <Badge variant="outline">Madurez {data.nivel_madurez_continuidad}</Badge>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="size-4 text-fulkro-primary-700" />
              Backups
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>Offsite</span>
              <StatusBadge value={data.tiene_backup_offsite} />
            </div>
            <div className="flex items-center justify-between">
              <span>Cifrado</span>
              <StatusBadge value={data.tiene_backup_cifrado} />
            </div>
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1">
                Última prueba <TooltipENS term="backup_policy" />
              </span>
              <span className="text-xs">{formatDate(data.ultima_prueba_restauracion)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Restauración OK</span>
              <StatusBadge value={data.prueba_restauracion_exitosa} />
            </div>
            <div className="text-xs text-fulkro-ink-500">
              {data.backups_inventario.length} entradas en inventario
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <FileWarning className="size-4 text-fulkro-primary-700" />
              DRP
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>DRP existe</span>
              <StatusBadge value={data.tiene_drp} />
            </div>
            <div className="flex items-center justify-between">
              <span>Documentado</span>
              <StatusBadge value={data.drp_documentado} />
            </div>
            <div className="flex items-center justify-between">
              <span>Probado</span>
              <StatusBadge value={data.drp_probado} />
            </div>
            <div className="flex items-center justify-between">
              <span>Última prueba</span>
              <span className="text-xs">{formatDate(data.drp_ultima_prueba)}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="size-4 text-fulkro-primary-700" />
              Objetivos globales
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1">
                RTO <TooltipENS term="RTO" />
              </span>
              <span className="font-mono">
                {data.rto_global_horas !== null ? `${data.rto_global_horas}h` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1">
                RPO <TooltipENS term="RPO" />
              </span>
              <span className="font-mono">
                {data.rpo_global_horas !== null ? `${data.rpo_global_horas}h` : "—"}
              </span>
            </div>
            <div className="text-xs text-fulkro-ink-500">
              {data.slas_proveedores.length} SLAs · {data.spofs_detectados.length} SPOFs
            </div>
          </CardContent>
        </Card>
      </div>

      {data.spofs_detectados.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm text-fulkro-warning">
              <AlertCircle className="size-4" />
              SPOFs detectados ({data.spofs_detectados.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {(data.spofs_detectados as Array<Record<string, unknown>>).map((s, i) => (
                <li key={i} className="text-fulkro-ink-700">
                  · {String(s.componente ?? s.nombre ?? s.descripcion ?? "—")}
                </li>
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
