/**
 * DossierPreview · Vista preview del dossier de auditoría (Motor 09).
 *
 * Lista de runs M09 + selección de run → muestra índice JSON con
 * recuento de secciones (documents / evidence / operational records)
 * + botón descarga ZIP. Reemplaza stub EmptyStateUpcoming.
 *
 * Backend pre-existing: m09_audit_prep prefix `/api/v1/audit-prep`.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileSearch, FileStack, Loader2, ScanSearch } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  auditPrepApi,
  type AuditPrepRun,
  type DossierIndex,
} from "@/lib/api/audit-prep";

export function DossierPreview({ projectId }: { projectId: string }) {
  const runs = useQuery<AuditPrepRun[]>({
    queryKey: ["m09", "runs", projectId],
    queryFn: () => auditPrepApi.listRuns(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!selectedRunId && runs.data && runs.data.length > 0) {
      setSelectedRunId(runs.data[0].id);
    }
  }, [runs.data, selectedRunId]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileStack size={16} /> Dossier de auditoría (M09)
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            Preview del dossier · runs de preparación + índice de secciones
            + descarga ZIP firmado
          </p>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <ScanSearch size={14} /> Runs de auditoría
          </CardTitle>
        </CardHeader>
        <CardContent>
          {runs.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : runs.isError ? (
            <Alert variant="danger">
              <AlertTitle>No se pudieron cargar los runs</AlertTitle>
              <AlertDescription>
                {runs.error instanceof Error ? runs.error.message : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : !runs.data || runs.data.length === 0 ? (
            <EmptyState
              title="Sin runs de preparación"
              description="Cuando se ejecute la primera preparación de auditoría aparecerá aquí."
            />
          ) : (
            <ul className="space-y-1.5">
              {runs.data.map((run) => (
                <li key={run.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedRunId(run.id)}
                    className={`flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left text-xs transition-colors ${
                      selectedRunId === run.id
                        ? "border-fulkro-primary-700 bg-fulkro-primary-700/5"
                        : "border-fulkro-ink-300/60 hover:bg-fulkro-ink-50"
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-fulkro-ink-700">
                        Run {run.id.slice(0, 8)}
                      </p>
                      <p className="mt-0.5 font-mono text-[10px] text-fulkro-ink-500">
                        {run.created_at
                          ? new Date(run.created_at).toLocaleString()
                          : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      {run.categoria ? (
                        <Badge variant="outline">{run.categoria}</Badge>
                      ) : null}
                      {run.status || run.estado ? (
                        <Badge variant="secondary">
                          {run.status ?? run.estado}
                        </Badge>
                      ) : null}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {selectedRunId ? (
        <DossierIndexCard projectId={projectId} runId={selectedRunId} />
      ) : null}
    </div>
  );
}

function DossierIndexCard({
  projectId,
  runId,
}: {
  projectId: string;
  runId: string;
}) {
  const index = useQuery<DossierIndex>({
    queryKey: ["m09", "dossier-index", projectId, runId],
    queryFn: () => auditPrepApi.dossierIndex(projectId, runId),
    enabled: Boolean(runId),
    staleTime: 60_000,
    retry: false,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2 text-sm">
          <span className="flex items-center gap-2">
            <FileSearch size={14} /> Índice del dossier · Run {runId.slice(0, 8)}
          </span>
          <div className="flex items-center gap-2">
            <a
              href={auditPrepApi.dossierDownloadUrl(projectId, runId)}
              download
              className="inline-flex items-center gap-1 rounded-md border border-fulkro-ink-300 px-3 py-1.5 text-xs font-medium text-fulkro-ink-700 hover:bg-fulkro-ink-50"
              data-testid="dossier-download-zip-unsigned"
            >
              <Download size={11} /> ZIP simple
            </a>
            <a
              href={auditPrepApi.dossierSignedDownloadUrl(projectId, runId)}
              download
              className="inline-flex items-center gap-1 rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-fulkro-primary-700/90"
              data-testid="dossier-download-zip-signed"
              title="MANIFEST.json firmado Ed25519 · entrega ENAC final"
            >
              <Download size={11} /> ZIP firmado (ENAC)
            </a>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {index.isLoading ? (
          <div className="flex items-center gap-2 text-xs text-fulkro-ink-500">
            <Loader2 size={11} className="animate-spin" /> cargando índice…
          </div>
        ) : index.isError ? (
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar el índice</AlertTitle>
            <AlertDescription>
              {index.error instanceof Error ? index.error.message : "Error desconocido"}
            </AlertDescription>
          </Alert>
        ) : !index.data ? (
          <p className="text-xs text-fulkro-ink-500">Sin datos</p>
        ) : (
          <SectionCounts data={index.data} />
        )}
      </CardContent>
    </Card>
  );
}

function SectionCounts({ data }: { data: DossierIndex }) {
  const sections: { key: string; label: string; count: number }[] = [
    {
      key: "documents",
      label: "Documentos",
      count: data.documents?.length ?? 0,
    },
    {
      key: "evidence",
      label: "Evidencias",
      count: data.evidence?.length ?? 0,
    },
    {
      key: "records",
      label: "Registros operativos",
      count: data.records?.length ?? 0,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-2 text-center sm:grid-cols-3 text-xs">
      {sections.map((s) => (
        <div
          key={s.key}
          className="rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-50/50 p-3"
        >
          <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
            {s.label}
          </p>
          <p className="mt-0.5 font-mono text-base font-semibold">{s.count}</p>
        </div>
      ))}
    </div>
  );
}
