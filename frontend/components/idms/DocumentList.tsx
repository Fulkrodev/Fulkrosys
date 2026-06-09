/**
 * DocumentList · 1.C.G.A v3.10 · admin tabla documentos folder selected.
 *
 * Reuse endpoint existing GET /api/v1/idms/projects/{id}/idms/documents.
 * Row actions: ver detalle · ver historial versiones.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, Eye, FileText, History } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { idmsApi, type IdmsDocument } from "@/lib/api/idms";

interface DocumentListProps {
  projectId: string;
  folderId: string | null;
  onOpenDocument: (documentId: string) => void;
  onOpenVersions: (documentId: string) => void;
}

export function DocumentList({
  projectId,
  folderId,
  onOpenDocument,
  onOpenVersions,
}: DocumentListProps) {
  const documents = useQuery({
    queryKey: ["idms", "documents", projectId, folderId ?? "ALL"],
    queryFn: () =>
      idmsApi.listDocuments(projectId, {
        folderId: folderId ?? undefined,
      }),
    enabled: Boolean(projectId),
    staleTime: 15_000,
  });

  if (documents.isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (documents.isError) {
    return (
      <p className="text-sm text-fulkro-danger">
        Error al cargar documentos.
      </p>
    );
  }

  const docs = documents.data?.documents ?? [];

  if (docs.length === 0) {
    return (
      <EmptyState
        title="Sin documentos en esta carpeta"
        description={
          folderId
            ? "Sube un documento o selecciona otra carpeta."
            : "Sube el primer documento del proyecto."
        }
      />
    );
  }

  return (
    <div className="rounded-lg border border-fulkro-ink-300">
      <table className="w-full text-sm">
        <thead className="border-b border-fulkro-ink-300 bg-fulkro-ink-50 text-left text-xs uppercase tracking-wider text-fulkro-ink-500">
          <tr>
            <th className="px-3 py-2">Nombre</th>
            <th className="px-3 py-2">Clasif.</th>
            <th className="px-3 py-2">Estado</th>
            <th className="px-3 py-2">Tamaño</th>
            <th className="px-3 py-2 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              projectId={projectId}
              onOpenDocument={onOpenDocument}
              onOpenVersions={onOpenVersions}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocumentRow({
  doc,
  projectId,
  onOpenDocument,
  onOpenVersions,
}: {
  doc: IdmsDocument;
  projectId: string;
  onOpenDocument: (id: string) => void;
  onOpenVersions: (id: string) => void;
}) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(false);
  const sizeKb = doc.file_size_bytes
    ? `${(doc.file_size_bytes / 1024).toFixed(1)} KB`
    : "—";

  // #32 (FRENTE B): descarga del binario desde el gestor admin (endpoint
  // streaming · resuelve storage_path minio:// durable con fallback local).
  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(false);
    try {
      await idmsApi.downloadDocument(projectId, doc.id, doc.nombre);
    } catch {
      setDownloadError(true);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <tr className="border-b border-fulkro-ink-200 last:border-b-0 hover:bg-fulkro-ink-50">
      <td className="px-3 py-2">
        <button
          type="button"
          onClick={() => onOpenDocument(doc.id)}
          className="flex items-center gap-2 text-left hover:underline"
        >
          <FileText size={14} className="text-fulkro-ink-500" />
          <span className="truncate">{doc.nombre}</span>
          {doc.version_actual ? (
            <span className="font-mono text-[10px] text-fulkro-ink-500">
              v{doc.version_actual}
            </span>
          ) : null}
        </button>
      </td>
      <td className="px-3 py-2">
        {doc.clasificacion ? (
          <Badge variant="outline" className="capitalize">
            {doc.clasificacion}
          </Badge>
        ) : (
          <span className="text-fulkro-ink-500">—</span>
        )}
      </td>
      <td className="px-3 py-2">
        {doc.estado ? (
          <Badge variant="secondary">{doc.estado}</Badge>
        ) : (
          <span className="text-fulkro-ink-500">—</span>
        )}
      </td>
      <td className="px-3 py-2 font-mono text-xs">{sizeKb}</td>
      <td className="px-3 py-2 text-right">
        <div className="inline-flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenDocument(doc.id)}
            aria-label="Ver detalle"
          >
            <Eye size={13} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenVersions(doc.id)}
            aria-label="Ver historial versiones"
          >
            <History size={13} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            disabled={downloading}
            aria-label={`Descargar ${doc.nombre}`}
            title={downloadError ? "Error al descargar · reintenta" : "Descargar"}
          >
            <Download
              size={13}
              className={downloadError ? "text-fulkro-danger-700" : undefined}
            />
          </Button>
        </div>
      </td>
    </tr>
  );
}
