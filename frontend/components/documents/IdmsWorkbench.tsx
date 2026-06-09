/**
 * IdmsWorkbench · K.X Workbench documental IDMS (Motor 24).
 *
 * Vista resumen del proyecto: stats counts + documentos recientes +
 * documentos expiring (acción rápida). El árbol completo y editor
 * detallado quedan para iteraciones siguientes.
 *
 * Backend: m24_idms prefix `/api/v1/idms` · paths repiten /idms/.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock, FileText, FolderTree, Loader2 } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  idmsApi,
  type IdmsDocument,
  type IdmsStats,
} from "@/lib/api/idms";

export function IdmsWorkbench({ projectId }: { projectId: string }) {
  const stats = useQuery<IdmsStats>({
    queryKey: ["m24", "idms-stats", projectId],
    queryFn: () => idmsApi.stats(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });

  const documents = useQuery({
    queryKey: ["m24", "idms-documents", projectId],
    queryFn: () => idmsApi.listDocuments(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const expiring = useQuery({
    queryKey: ["m24", "idms-expiring", projectId],
    queryFn: () => idmsApi.expiring(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });

  const expiringDocs: IdmsDocument[] = Array.isArray(expiring.data)
    ? expiring.data
    : (expiring.data?.documents ?? []);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FolderTree size={16} /> Workbench documental (IDMS)
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            Resumen documental del proyecto · Motor 24 IDMS
          </p>
        </CardHeader>
      </Card>

      <StatsBlock query={stats} />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileText size={14} /> Documentos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {documents.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : documents.isError ? (
            <Alert variant="danger">
              <AlertTitle>No se pudo cargar documentos</AlertTitle>
              <AlertDescription>
                {documents.error instanceof Error
                  ? documents.error.message
                  : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : !documents.data || documents.data.documents.length === 0 ? (
            <EmptyState
              title="Sin documentos"
              description="Cuando se generen documentos del proyecto aparecerán aquí."
            />
          ) : (
            <ul className="space-y-1.5">
              {documents.data.documents.slice(0, 30).map((d) => (
                <DocumentRow key={d.id} doc={d} />
              ))}
              {documents.data.documents.length > 30 ? (
                <li className="pt-1 text-[11px] text-fulkro-ink-500">
                  …y {documents.data.documents.length - 30} más
                </li>
              ) : null}
            </ul>
          )}
        </CardContent>
      </Card>

      {expiringDocs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Clock size={14} className="text-amber-600" />
              Documentos próximos a caducar ({expiringDocs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {expiringDocs.slice(0, 10).map((d) => (
                <DocumentRow key={d.id} doc={d} highlight />
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function StatsBlock({
  query,
}: {
  query: ReturnType<typeof useQuery<IdmsStats>>;
}) {
  if (query.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-4 text-xs text-fulkro-ink-500">
          <Loader2 size={12} className="animate-spin" /> cargando estadísticas…
        </CardContent>
      </Card>
    );
  }
  if (query.isError || !query.data) {
    return null;
  }
  const stats = query.data;
  const total = (stats.total_documents as number) ?? 0;
  const totalFolders = (stats.total_folders as number) ?? 0;
  const sizeMb = stats.total_size_bytes
    ? ((stats.total_size_bytes as number) / (1024 * 1024)).toFixed(1)
    : null;

  return (
    <Card>
      <CardContent className="grid grid-cols-3 gap-2 p-4 text-center text-xs">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
            Documentos
          </p>
          <p className="mt-0.5 font-mono text-base font-semibold">{total}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
            Carpetas
          </p>
          <p className="mt-0.5 font-mono text-base font-semibold">{totalFolders}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
            Total
          </p>
          <p className="mt-0.5 font-mono text-base font-semibold">
            {sizeMb !== null ? `${sizeMb} MB` : "—"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function DocumentRow({
  doc,
  highlight,
}: {
  doc: IdmsDocument;
  highlight?: boolean;
}) {
  return (
    <li
      className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 ${
        highlight
          ? "border-amber-300 bg-amber-50/50"
          : "border-fulkro-ink-300/60"
      }`}
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {doc.nombre}
        </p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 font-mono text-[10px] text-fulkro-ink-500">
          {doc.template_codigo ? <span>{doc.template_codigo}</span> : null}
          {doc.version ? <span>v{doc.version}</span> : null}
          {doc.tipo ? <span>{doc.tipo}</span> : null}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {doc.estado ? (
          <Badge variant="secondary">{doc.estado}</Badge>
        ) : null}
        {doc.clasificacion ? (
          <Badge variant="outline">{doc.clasificacion}</Badge>
        ) : null}
      </div>
    </li>
  );
}
