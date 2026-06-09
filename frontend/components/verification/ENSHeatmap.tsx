"use client";

import { Loader2, Info } from "lucide-react";
import * as React from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { useHeatmap } from "@/hooks/useVerification";
import type { HeatmapCell, HeatmapStatus } from "@/lib/verification-types";
import { cn } from "@/lib/utils";

const STATUS_CLASSES: Record<HeatmapStatus, { cell: string; label: string }> = {
  compliant: {
    cell: "bg-fulkro-success text-white border-fulkro-success/40",
    label: "Conforme",
  },
  partial: {
    cell: "bg-fulkro-warning text-white border-fulkro-warning/40",
    label: "Parcial",
  },
  non_compliant: {
    cell: "bg-fulkro-danger text-white border-fulkro-danger/40",
    label: "No conforme",
  },
  not_verified: {
    cell: "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)] border-[color:var(--fulkro-surface-glass-border)]",
    label: "No verificado",
  },
};

/**
 * Agrupa celdas por familia (prefijo antes del primer punto) para mostrar
 * el heatmap en secciones visuales (org, op.pl, op.acc, op.exp, ...).
 */
function groupByFamily(cells: HeatmapCell[]): Record<string, HeatmapCell[]> {
  const out: Record<string, HeatmapCell[]> = {};
  for (const c of cells) {
    const parts = c.measure.split(".");
    const key = parts.length >= 2 ? `${parts[0]}.${parts[1]}` : parts[0];
    (out[key] ??= []).push(c);
  }
  return out;
}

const FAMILY_LABELS: Record<string, string> = {
  "org": "Marco organizativo",
  "op.pl": "Planificación",
  "op.acc": "Control de acceso",
  "op.exp": "Explotación",
  "op.ext": "Servicios externos",
  "op.nub": "Nube",
  "op.cont": "Continuidad",
  "op.mon": "Monitorización",
  "mp.if": "Instalaciones",
  "mp.per": "Personal",
  "mp.eq": "Equipos",
  "mp.com": "Comunicaciones",
  "mp.si": "Soportes de información",
  "mp.sw": "Software",
  "mp.info": "Información",
  "mp.s": "Servicios",
};

export function ENSHeatmap({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useHeatmap(projectId);
  const [hovered, setHovered] = React.useState<HeatmapCell | null>(null);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Mapa de calor ENS Anexo II</CardTitle>
        </CardHeader>
        <CardContent className="flex h-40 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
          <Loader2 size={14} className="animate-spin" /> calculando cobertura…
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Mapa de calor ENS Anexo II</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          No se pudo obtener el heatmap: {(error as Error)?.message ?? "error"}
        </CardContent>
      </Card>
    );
  }

  const grouped = groupByFamily(data.cells);
  const families = Object.keys(FAMILY_LABELS).filter((f) => grouped[f]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <div>
          <CardTitle>
            Mapa de calor <InfoTag term="ENS" display="ENS" /> ·{" "}
            <InfoTag term="Anexo_II" display="Anexo II" /> (73 medidas)
          </CardTitle>
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            {data.summary.compliant} conformes ·{" "}
            <span className="text-fulkro-warning font-semibold">
              {data.summary.partial}
            </span>{" "}
            parciales ·{" "}
            <span className="text-fulkro-danger font-semibold">
              {data.summary.non_compliant}
            </span>{" "}
            no conformes · {data.summary.not_verified} no verificadas
          </p>
        </div>
        <Legend />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {families.map((fam) => (
          <div key={fam}>
            <p className="mb-1 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              {FAMILY_LABELS[fam]} · {fam}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {grouped[fam].map((cell) => {
                const style = STATUS_CLASSES[cell.status];
                return (
                  <button
                    type="button"
                    key={cell.measure}
                    onMouseEnter={() => setHovered(cell)}
                    onMouseLeave={() => setHovered(null)}
                    onFocus={() => setHovered(cell)}
                    onBlur={() => setHovered(null)}
                    aria-label={`${cell.measure} ${style.label} ${cell.findings_count} hallazgos`}
                    className={cn(
                      "rounded-md border px-2 py-1 font-mono text-[10px] transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-fulkro-primary-500/40",
                      style.cell,
                    )}
                  >
                    {cell.measure}
                    {cell.findings_count > 0 && (
                      <span className="ml-1 rounded bg-white/30 px-1 text-[9px]">
                        {cell.findings_count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        {hovered && (
          <div
            role="tooltip"
            className="sticky bottom-2 flex items-start gap-2 rounded-md border border-fulkro-primary-700/20 bg-white p-3 text-xs shadow-lg"
          >
            <Info size={14} className="mt-0.5 text-fulkro-primary-700" />
            <div>
              <p className="font-semibold text-fulkro-primary-700">{hovered.measure}</p>
              <p className="text-fulkro-ink-500">
                Estado: {STATUS_CLASSES[hovered.status].label} ·{" "}
                {hovered.findings_count} hallazgos
                {hovered.worst_severity &&
                  ` · peor severidad ${hovered.worst_severity}`}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap gap-2 text-[10px]">
      {(Object.keys(STATUS_CLASSES) as HeatmapStatus[]).map((k) => (
        <span key={k} className="flex items-center gap-1">
          <span
            className={cn("inline-block h-3 w-3 rounded", STATUS_CLASSES[k].cell)}
          />
          {STATUS_CLASSES[k].label}
        </span>
      ))}
    </div>
  );
}
