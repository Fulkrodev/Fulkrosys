"use client";

import * as React from "react";
import { Copy, ExternalLink, GitBranch, Globe } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import { useDataFlows, useGenerateDataFlows, useDiscoveryRuns } from "@/hooks/useDiscovery";
import type { DataFlowDiagram } from "@/lib/admin-discovery/api";

export interface DataFlowTabProps {
  projectId: string;
}

function buildMermaidLiveLink(code: string): string {
  // mermaid.live encoded URL: base64 of state JSON
  const state = { code, mermaid: { theme: "default" } };
  const json = JSON.stringify(state);
  const b64 = typeof window !== "undefined"
    ? btoa(unescape(encodeURIComponent(json)))
    : "";
  return `https://mermaid.live/edit#base64:${b64}`;
}

function DataFlowCard({ dfd }: { dfd: DataFlowDiagram }) {
  const crossBorderFlows = (dfd.flujos as Array<Record<string, unknown>>).filter(
    (f) => f.cross_border === true || f.cross_border_eu === true,
  );
  const hasMermaid = !!dfd.mermaid_code;

  const copyMermaid = async () => {
    if (!dfd.mermaid_code) return;
    try {
      await navigator.clipboard.writeText(dfd.mermaid_code);
      toast.success("Mermaid copiado al portapapeles");
    } catch {
      toast.error("No se pudo copiar");
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{dfd.nombre}</CardTitle>
            {dfd.descripcion ? (
              <CardDescription>{dfd.descripcion}</CardDescription>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{dfd.tipo}</Badge>
            <Badge variant="info">{dfd.clasificacion_max_datos}</Badge>
            {crossBorderFlows.length > 0 ? (
              <TooltipENS term="RGPD_Art_49">
                <Badge variant="warning">
                  <Globe className="mr-1 size-3" /> {crossBorderFlows.length} cross-border
                </Badge>
              </TooltipENS>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {hasMermaid ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={copyMermaid}>
                <Copy className="mr-1 size-3.5" /> Copiar
              </Button>
              <button
                type="button"
                onClick={() => {
                  // §1.6: abrir el diagrama en mermaid.live envía la arquitectura
                  // interna (nodos, almacenes, protocolos) a un servicio externo.
                  // Avisar al admin y exigir confirmación explícita antes de salir.
                  const ok = window.confirm(
                    "Este diagrama (arquitectura interna del proyecto) se enviará a " +
                      "mermaid.live, un servicio EXTERNO. ¿Continuar?",
                  );
                  if (ok) {
                    window.open(
                      buildMermaidLiveLink(dfd.mermaid_code ?? ""),
                      "_blank",
                      "noopener,noreferrer",
                    );
                  }
                }}
                className="inline-flex items-center gap-1 text-xs text-fulkro-primary-700 hover:underline"
              >
                <ExternalLink className="size-3" />
                Abrir en mermaid.live
              </button>
            </div>
            <pre className="max-h-72 overflow-auto rounded border border-fulkro-ink-100 bg-fulkro-canvas p-3 text-xs">
              {dfd.mermaid_code}
            </pre>
          </div>
        ) : null}

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="font-medium text-fulkro-ink-700">Nodos ({dfd.nodos.length})</p>
            <ul className="mt-1 space-y-1">
              {(dfd.nodos as Array<Record<string, unknown>>).slice(0, 6).map((n, i) => (
                <li key={i} className="text-fulkro-ink-500">
                  · {String(n.nombre ?? n.id ?? i)}
                </li>
              ))}
              {dfd.nodos.length > 6 ? (
                <li className="text-fulkro-ink-300">+{dfd.nodos.length - 6} más</li>
              ) : null}
            </ul>
          </div>
          <div>
            <p className="font-medium text-fulkro-ink-700">Flujos ({dfd.flujos.length})</p>
            <ul className="mt-1 space-y-1">
              {(dfd.flujos as Array<Record<string, unknown>>).slice(0, 6).map((f, i) => (
                <li key={i} className="text-fulkro-ink-500">
                  · {String(f.origen ?? f.source ?? "?")} → {String(f.destino ?? f.destination ?? "?")}
                </li>
              ))}
              {dfd.flujos.length > 6 ? (
                <li className="text-fulkro-ink-300">+{dfd.flujos.length - 6} más</li>
              ) : null}
            </ul>
          </div>
        </div>

        {dfd.observaciones_seguridad.length > 0 ? (
          <div className="rounded border border-fulkro-warning/30 bg-fulkro-warning/5 p-3 text-xs">
            <p className="font-medium text-fulkro-warning">
              Observaciones seguridad ({dfd.observaciones_seguridad.length})
            </p>
            <ul className="mt-1 space-y-1">
              {(dfd.observaciones_seguridad as Array<Record<string, unknown>>).slice(0, 4).map(
                (o, i) => (
                  <li key={i}>· {String(o.titulo ?? o.descripcion ?? o.codigo ?? "—")}</li>
                ),
              )}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function DataFlowTab({ projectId }: DataFlowTabProps) {
  const { data: dfds = [], isLoading } = useDataFlows(projectId);
  const { data: runs = [] } = useDiscoveryRuns(projectId);
  const generateMutation = useGenerateDataFlows(projectId);

  const lastCompletedRun = runs.find((r) => r.status === "completed");

  const handleGenerate = () => {
    if (!lastCompletedRun) {
      toast.warning("Necesitas un run completado previamente");
      return;
    }
    generateMutation.mutate(
      { run_id: lastCompletedRun.id },
      {
        onSuccess: (res) => {
          toast.success(`${res.generated} diagramas generados`);
        },
        onError: () => toast.error("Error al generar diagramas"),
      },
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <GitBranch size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Flujos de datos
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">({dfds.length})</span>
          </h3>
          <TooltipENS term="dataflow" />
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={handleGenerate}
          disabled={!lastCompletedRun || generateMutation.isPending}
        >
          {generateMutation.isPending ? "Generando…" : "Regenerar diagramas"}
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-fulkro-ink-500">Cargando diagramas…</p>
      ) : dfds.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded border border-dashed border-fulkro-ink-200 py-10 text-fulkro-ink-500">
          <GitBranch className="size-8" />
          <p className="text-sm">Sin diagramas generados · ejecuta un scan completo</p>
        </div>
      ) : (
        <div className="space-y-4">
          {dfds.map((dfd) => (
            <DataFlowCard key={dfd.id} dfd={dfd} />
          ))}
        </div>
      )}
    </div>
  );
}
